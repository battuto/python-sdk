################################################################################
# Copyright IBM Corporation 2024
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
################################################################################

"""Wrapper for the codeanalyzer-go binary."""

import json
import logging
import os
import platform
import shlex
import subprocess
import sys
from importlib import resources
from pathlib import Path
from typing import Dict, List, Optional, Union

import networkx as nx

from cldk.analysis import AnalysisLevel
from cldk.models.go.models import GoAnalysis, GoCallGraph, GoPackage, GoSymbolTable
from cldk.utils.exceptions.exceptions import CodeanalyzerExecutionException

logger = logging.getLogger(__name__)


class GCodeanalyzer:
    """A class for building the application view of a Go application using codeanalyzer-go.

    Args:
        project_dir (str or Path): The path to the root of the Go project.
        source_code (str, optional): The source code of a single Go file to analyze. Defaults to None.
        analysis_backend_path (str or Path, optional): The path to the codeanalyzer-go executable.
        analysis_json_path (str or Path, optional): The path to save the intermediate code analysis outputs.
        analysis_level (str): The level of analysis ('symbol_table', 'call_graph', or 'full').
        eager_analysis (bool): If True, the analysis will be performed every time the object is created.
        include_tests (bool): If True, include test files in the analysis.
        exclude_dirs (List[str], optional): List of directories to exclude from analysis.
        cg_algorithm (str): Call graph algorithm to use ('cha' or 'rta').
        only_pkg (str, optional): Only analyze packages matching this filter.
        emit_positions (str): Position detail level ('detailed' or 'minimal').
    """

    def __init__(
        self,
        project_dir: Union[str, Path],
        source_code: Optional[str] = None,
        analysis_backend_path: Optional[Union[str, Path]] = None,
        analysis_json_path: Optional[Union[str, Path]] = None,
        analysis_level: str = AnalysisLevel.symbol_table,
        eager_analysis: bool = False,
        include_tests: bool = False,
        exclude_dirs: Optional[List[str]] = None,
        cg_algorithm: str = "cha",
        only_pkg: Optional[str] = None,
        emit_positions: str = "detailed",
        include_body: bool = False,
        compact: bool = False,
    ) -> None:
        """Initialize the GCodeanalyzer."""
        self.project_dir = Path(project_dir) if project_dir else None
        self.source_code = source_code
        self.analysis_backend_path = Path(analysis_backend_path) if analysis_backend_path else None
        self.analysis_json_path = Path(analysis_json_path) if analysis_json_path else None
        self.analysis_level = analysis_level
        self.eager_analysis = eager_analysis
        self.include_tests = include_tests
        self.exclude_dirs = exclude_dirs or []
        self.cg_algorithm = cg_algorithm
        self.only_pkg = only_pkg
        self.emit_positions = emit_positions
        self.include_body = include_body
        self.compact = compact

        # Initialize analysis
        self.application: Optional[GoAnalysis] = None
        self._compact_data: Optional[Dict] = None
        self.call_graph: Optional[nx.DiGraph] = None

        if self.source_code is None and self.project_dir:
            if self.compact:
                self._init_compact_analysis()
            else:
                self._init_codeanalyzer()

    def _get_codeanalyzer_exec(self) -> str:
        """Get the path to the codeanalyzer-go executable.

        Resolution order:
        1. Explicitly provided ``analysis_backend_path``
        2. Bundled binary shipped inside the CLDK package
        3. ``codeanalyzer-go`` on the system PATH
        4. ``CODEANALYZER_GO_PATH`` environment variable

        Returns:
            str: The path to the codeanalyzer-go executable.

        Raises:
            CodeanalyzerExecutionException: If the executable cannot be found.
        """
        # 1. If analysis_backend_path is provided, use it
        if self.analysis_backend_path:
            if self.analysis_backend_path.exists() and self.analysis_backend_path.is_file():
                return str(self.analysis_backend_path)
            else:
                raise CodeanalyzerExecutionException(
                    f"Provided codeanalyzer-go path does not exist: {self.analysis_backend_path}"
                )

        # 2. Try bundled binary (same pattern as Java JAR)
        bundled_path = self._get_bundled_binary()
        if bundled_path:
            return bundled_path

        # 3. Try to find codeanalyzer-go in PATH
        codeanalyzer_go = "codeanalyzer-go.exe" if os.name == "nt" else "codeanalyzer-go"
        from shutil import which
        exec_path = which(codeanalyzer_go)
        if exec_path:
            return exec_path

        # 4. Check environment variable
        env_path = os.getenv("CODEANALYZER_GO_PATH")
        if env_path and Path(env_path).exists():
            return env_path

        raise CodeanalyzerExecutionException(
            "codeanalyzer-go executable not found. Please provide analysis_backend_path, "
            "add it to PATH, or set CODEANALYZER_GO_PATH environment variable."
        )

    def _get_bundled_binary(self) -> Optional[str]:
        """Resolve the platform-specific bundled codeanalyzer-go binary.

        Returns:
            str | None: Path to the bundled binary if it exists, None otherwise.
        """
        system = platform.system().lower()   # "windows", "linux", "darwin"
        machine = platform.machine().lower() # "amd64", "x86_64", "arm64", "aarch64"

        # Normalize machine name
        if machine in ("x86_64", "amd64"):
            machine = "amd64"
        elif machine in ("aarch64", "arm64"):
            machine = "arm64"

        suffix = ".exe" if system == "windows" else ""
        binary_name = f"codeanalyzer-go-{system}-{machine}{suffix}"

        try:
            with resources.as_file(
                resources.files("cldk.analysis.go.codeanalyzer.bin")
            ) as bin_path:
                bundled = bin_path / binary_name
                if bundled.exists():
                    # Ensure the binary is executable on Unix
                    if system != "windows":
                        bundled.chmod(0o755)
                    logger.info(f"Using bundled codeanalyzer-go binary: {bundled}")
                    return str(bundled)
        except Exception as e:
            logger.debug(f"Could not resolve bundled binary: {e}")

        return None

    def _build_command(self, output_dir: Path) -> List[str]:
        """Build the command to execute codeanalyzer-go.

        Args:
            output_dir (Path): The directory where analysis output will be written.

        Returns:
            List[str]: The command as a list of strings.
        """
        exec_path = self._get_codeanalyzer_exec()
        cmd = [exec_path]

        # Input project path
        cmd.extend(["--input", str(self.project_dir)])

        # Output directory
        cmd.extend(["--output", str(output_dir)])

        # Analysis level
        level_map = {
            AnalysisLevel.symbol_table: "symbol_table",
            AnalysisLevel.call_graph: "call_graph",
            "full": "full",
        }
        cmd.extend(["--analysis-level", level_map.get(self.analysis_level, "symbol_table")])

        # Call graph algorithm
        if self.analysis_level in [AnalysisLevel.call_graph, "full"]:
            cmd.extend(["--cg", self.cg_algorithm])

        # Include tests
        if self.include_tests:
            cmd.append("--include-tests")

        # Exclude directories
        if self.exclude_dirs:
            cmd.extend(["--exclude-dirs", ",".join(self.exclude_dirs)])

        # Package filter
        if self.only_pkg:
            cmd.extend(["--only-pkg", self.only_pkg])

        # Emit positions
        cmd.extend(["--emit-positions", self.emit_positions])

        # Include body (enables call_examples)
        if self.include_body:
            cmd.append("--include-body")

        # Compact mode (LLM-optimized output)
        if self.compact:
            cmd.append("--compact")

        # Output format
        cmd.extend(["--format", "json"])

        return cmd

    def _run_analysis(self) -> Path:
        """Execute the codeanalyzer-go binary.

        Returns:
            Path: The path to the generated analysis.json file.

        Raises:
            CodeanalyzerExecutionException: If the analysis fails.
        """
        # Determine output directory
        if self.analysis_json_path:
            output_dir = self.analysis_json_path.parent
            output_dir.mkdir(parents=True, exist_ok=True)
        else:
            output_dir = self.project_dir / ".cldk_output"
            output_dir.mkdir(parents=True, exist_ok=True)

        # Build and execute command
        cmd = self._build_command(output_dir)
        logger.info(f"Executing codeanalyzer-go: {' '.join(shlex.quote(str(c)) for c in cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                cwd=self.project_dir,
            )
            logger.debug(f"codeanalyzer-go stdout: {result.stdout}")
            if result.stderr:
                logger.warning(f"codeanalyzer-go stderr: {result.stderr}")
        except subprocess.CalledProcessError as e:
            logger.error(f"codeanalyzer-go failed with exit code {e.returncode}")
            logger.error(f"stdout: {e.stdout}")
            logger.error(f"stderr: {e.stderr}")
            raise CodeanalyzerExecutionException(
                f"codeanalyzer-go execution failed: {e.stderr}"
            ) from e

        # Find the analysis.json file
        analysis_json = output_dir / "analysis.json"
        if not analysis_json.exists():
            raise CodeanalyzerExecutionException(
                f"Expected analysis.json not found at {analysis_json}"
            )

        return analysis_json

    def _load_analysis_json(self, json_path: Path) -> GoAnalysis:
        """Load and parse the analysis.json file.

        Args:
            json_path (Path): The path to the analysis.json file.

        Returns:
            GoAnalysis: The parsed analysis model.

        Raises:
            CodeanalyzerExecutionException: If parsing fails.
        """
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Validate and parse using Pydantic
            analysis = GoAnalysis.model_validate(data)
            logger.info("Successfully loaded and validated analysis.json")
            return analysis
        except Exception as e:
            logger.error(f"Failed to parse analysis.json: {e}")
            raise CodeanalyzerExecutionException(
                f"Failed to parse analysis.json: {e}"
            ) from e

    def _init_codeanalyzer(self) -> GoAnalysis:
        """Initialize the codeanalyzer by running the analysis.

        Returns:
            GoAnalysis: The application view of the Go code.
        """
        # Check if we should reuse existing analysis
        if self.analysis_json_path and self.analysis_json_path.exists() and not self.eager_analysis:
            logger.info(f"Reusing existing analysis from {self.analysis_json_path}")
            self.application = self._load_analysis_json(self.analysis_json_path)
        else:
            # Run fresh analysis
            logger.info("Running fresh Go code analysis")
            analysis_json_path = self._run_analysis()
            self.application = self._load_analysis_json(analysis_json_path)

        # Generate call graph if needed
        if self.analysis_level in [AnalysisLevel.call_graph, "full"] and self.application.call_graph:
            self.call_graph = self._generate_call_graph()

        return self.application

    def _generate_call_graph(self) -> nx.DiGraph:
        """Generate a NetworkX directed graph from the call graph data.

        Returns:
            nx.DiGraph: The call graph as a NetworkX graph.
        """
        if not self.application or not self.application.call_graph:
            logger.warning("No call graph data available")
            return nx.DiGraph()

        graph = nx.DiGraph()
        cg = self.application.call_graph

        # Add nodes
        for node in cg.nodes:
            graph.add_node(
                node.id,
                qualified_name=node.qualified_name,
                package=node.package,
                name=node.name,
                kind=node.kind,
                receiver_type=node.receiver_type,
                position=node.position.model_dump() if node.position else None,
            )

        # Add edges
        for edge in cg.edges:
            graph.add_edge(
                edge.source,
                edge.target,
                kind=edge.kind,
                position=edge.position.model_dump() if edge.position else None,
            )

        logger.info(f"Generated call graph with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")
        return graph

    def get_application_view(self) -> GoAnalysis:
        """Return the application view of the Go code.

        Returns:
            GoAnalysis: The complete analysis result.
        """
        if self.application is None:
            self._init_codeanalyzer()
        return self.application

    def get_symbol_table(self) -> Dict[str, GoPackage]:
        """Return the symbol table.

        Returns:
            Dict[str, GoPackage]: Symbol table keyed by package path.
        """
        app = self.get_application_view()
        if app.symbol_table:
            return app.symbol_table.packages
        return {}

    def get_packages(self) -> List[GoPackage]:
        """Return all packages in the Go project.

        Returns:
            List[GoPackage]: List of all packages.
        """
        symbol_table = self.get_symbol_table()
        return list(symbol_table.values())

    def get_call_graph(self) -> nx.DiGraph:
        """Return the call graph as a NetworkX DiGraph.

        Returns:
            nx.DiGraph: The call graph.
        """
        if self.call_graph is None and self.application and self.application.call_graph:
            self.call_graph = self._generate_call_graph()
        return self.call_graph if self.call_graph else nx.DiGraph()

    def get_call_graph_json(self) -> str:
        """Return the call graph as a JSON string.

        Returns:
            str: JSON representation of the call graph.
        """
        app = self.get_application_view()
        if app.call_graph:
            return app.call_graph.model_dump_json(indent=2)
        return "{}"

    # ──────────────────────────────────────────────────────────────────────────
    # Compact mode support
    # ──────────────────────────────────────────────────────────────────────────

    def _init_compact_analysis(self) -> Dict:
        """Run analysis in compact mode and store raw dict (no Pydantic validation).

        Returns:
            Dict: The raw compact JSON data.
        """
        if self._compact_data is not None and not self.eager_analysis:
            return self._compact_data

        analysis_json_path = self._run_analysis()
        try:
            with open(analysis_json_path, "r", encoding="utf-8") as f:
                self._compact_data = json.load(f)
            logger.info("Successfully loaded compact analysis JSON")
        except Exception as e:
            logger.error(f"Failed to parse compact analysis.json: {e}")
            raise CodeanalyzerExecutionException(
                f"Failed to parse compact analysis.json: {e}"
            ) from e

        return self._compact_data

    def get_compact_view(self) -> Dict:
        """Return the compact analysis data as a raw dictionary.

        The compact output uses abbreviated keys (p, n, d, c, e, etc.)
        optimized for LLM consumption. This bypasses Pydantic validation
        since the compact schema differs from the standard one.

        Returns:
            Dict: The raw compact JSON data.
        """
        if self._compact_data is None:
            self._compact_data = self._init_compact_analysis()
        return self._compact_data
