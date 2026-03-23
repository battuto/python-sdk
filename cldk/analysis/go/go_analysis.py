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

"""Go analysis utilities.

Provides a high-level API to analyze Go projects using the codeanalyzer-go backend.
"""

from pathlib import Path
from typing import Dict, List, Optional, Union

import networkx as nx

from cldk.analysis.go.codeanalyzer import GCodeanalyzer
from cldk.models.go.models import (
    GoAnalysis as GoAnalysisModel,
    GoCallableDecl,
    GoCLDKPDG,
    GoCLDKSDG,
    GoFunctionPDG,
    GoPackage,
    GoPackagePDG,
    GoPackageSDG,
    GoTypeDecl,
)


class GoAnalysis:
    """Analysis façade for Go code.

    This class exposes methods to query symbol tables, packages, types, functions,
    and call graphs for a Go project.
    """

    def __init__(
        self,
        project_dir: Union[str, Path, None],
        source_code: Optional[str] = None,
        analysis_backend_path: Optional[Union[str, Path]] = None,
        analysis_json_path: Optional[Union[str, Path]] = None,
        analysis_level: str = "symbol_table",
        eager_analysis: bool = False,
        include_tests: bool = False,
        exclude_dirs: Optional[List[str]] = None,
        cg_algorithm: str = "cha",
        only_pkg: Optional[str] = None,
        emit_positions: str = "detailed",
        include_body: bool = False,
        compact: bool = False,
    ) -> None:
        """Initialize the Go analysis backend.

        Args:
            project_dir (str | Path | None): Directory path of the Go project.
            source_code (str | None): Source text for single-file analysis (not yet supported).
            analysis_backend_path (str | Path | None): Path to the codeanalyzer-go executable.
            analysis_json_path (str | Path | None): Path to persist the analysis.json.
            analysis_level (str): Analysis level ("symbol_table", "call_graph", or "full").
            eager_analysis (bool): If True, forces regeneration of analysis.json.
            include_tests (bool): If True, include test files in analysis.
            exclude_dirs (List[str] | None): Directories to exclude from analysis.
            cg_algorithm (str): Call graph algorithm ("cha" or "rta").
            only_pkg (str | None): Only analyze packages matching this filter.
            emit_positions (str): Position detail level ("detailed" or "minimal").
            compact (bool): If True, run analysis in compact (LLM-optimized) mode.
        """
        self.project_dir = project_dir
        self.source_code = source_code
        self.analysis_level = analysis_level
        self.analysis_json_path = analysis_json_path
        self.analysis_backend_path = analysis_backend_path
        self.eager_analysis = eager_analysis
        self.include_tests = include_tests
        self.exclude_dirs = exclude_dirs
        self.cg_algorithm = cg_algorithm
        self.only_pkg = only_pkg
        self.emit_positions = emit_positions
        self.include_body = include_body
        self.compact = compact

        # Initialize the analysis backend
        self.backend: GCodeanalyzer = GCodeanalyzer(
            project_dir=self.project_dir,
            source_code=self.source_code,
            analysis_backend_path=self.analysis_backend_path,
            analysis_json_path=self.analysis_json_path,
            analysis_level=self.analysis_level,
            eager_analysis=self.eager_analysis,
            include_tests=self.include_tests,
            exclude_dirs=self.exclude_dirs,
            cg_algorithm=self.cg_algorithm,
            only_pkg=self.only_pkg,
            emit_positions=self.emit_positions,
            include_body=self.include_body,
            compact=self.compact,
        )

    def get_application_view(self) -> GoAnalysisModel:
        """Return the application view of the Go code.

        Returns:
            GoAnalysisModel: Complete analysis result including metadata, symbol table, and call graph.

        Raises:
            NotImplementedError: If single-file mode is used (not yet supported).

        Examples:
            Get an application view using a project directory:

            >>> from cldk.analysis import AnalysisLevel
            >>> ga = GoAnalysis(
            ...     project_dir='path/to/go/project',
            ...     analysis_level=AnalysisLevel.symbol_table
            ... )
            >>> app = ga.get_application_view()  # doctest: +SKIP
        """
        if self.source_code:
            raise NotImplementedError("Single-file analysis for Go is not yet supported.")
        return self.backend.get_application_view()

    def get_symbol_table(self) -> Dict[str, GoPackage]:
        """Return the symbol table.

        Returns:
            Dict[str, GoPackage]: Symbol table keyed by package path.

        Examples:
            >>> ga = GoAnalysis(project_dir='path/to/go/project')
            >>> symbol_table = ga.get_symbol_table()  # doctest: +SKIP
            >>> isinstance(symbol_table, dict)  # doctest: +SKIP
            True
        """
        return self.backend.get_symbol_table()

    def get_packages(self) -> List[GoPackage]:
        """Return all packages in the Go project.

        Returns:
            List[GoPackage]: List of all packages analyzed.

        Examples:
            >>> from cldk import CLDK
            >>> ga = CLDK(language="go").analysis(project_path='path/to/go/project')
            >>> packages = ga.get_packages()  # doctest: +SKIP
            >>> for pkg in packages:  # doctest: +SKIP
            ...     print(pkg.name, pkg.path)
        """
        return self.backend.get_packages()

    def get_functions(self, package: Optional[str] = None) -> Dict[str, GoCallableDecl]:
        """Return functions/methods from the specified package or all packages.

        Args:
            package (str | None): Package path to filter by. If None, returns all functions.

        Returns:
            Dict[str, GoCallableDecl]: Functions keyed by qualified name.

        Examples:
            >>> ga = GoAnalysis(project_dir='path/to/go/project')
            >>> all_functions = ga.get_functions()  # doctest: +SKIP
            >>> main_functions = ga.get_functions(package="main")  # doctest: +SKIP
        """
        symbol_table = self.get_symbol_table()
        functions = {}

        if package:
            # Return functions from specified package only
            if package in symbol_table:
                pkg = symbol_table[package]
                functions.update(pkg.callable_declarations)
                # Also include methods from types
                for type_decl in pkg.type_declarations.values():
                    functions.update(type_decl.methods)
        else:
            # Return functions from all packages
            for pkg in symbol_table.values():
                functions.update(pkg.callable_declarations)
                # Also include methods from types
                for type_decl in pkg.type_declarations.values():
                    functions.update(type_decl.methods)

        return functions

    def get_types(self, package: Optional[str] = None) -> Dict[str, GoTypeDecl]:
        """Return type declarations from the specified package or all packages.

        Args:
            package (str | None): Package path to filter by. If None, returns all types.

        Returns:
            Dict[str, GoTypeDecl]: Type declarations keyed by qualified name.

        Examples:
            >>> ga = GoAnalysis(project_dir='path/to/go/project')
            >>> all_types = ga.get_types()  # doctest: +SKIP
            >>> main_types = ga.get_types(package="main")  # doctest: +SKIP
        """
        symbol_table = self.get_symbol_table()
        types = {}

        if package:
            # Return types from specified package only
            if package in symbol_table:
                types.update(symbol_table[package].type_declarations)
        else:
            # Return types from all packages
            for pkg in symbol_table.values():
                types.update(pkg.type_declarations)

        return types

    def get_call_graph(self) -> nx.DiGraph:
        """Return the call graph as a NetworkX directed graph.

        Returns:
            nx.DiGraph: Call graph with nodes representing functions/methods and edges
            representing calls between them.

        Examples:
            >>> from cldk.analysis import AnalysisLevel
            >>> ga = GoAnalysis(
            ...     project_dir='path/to/go/project',
            ...     analysis_level=AnalysisLevel.call_graph
            ... )
            >>> cg = ga.get_call_graph()  # doctest: +SKIP
            >>> print(f"Nodes: {cg.number_of_nodes()}, Edges: {cg.number_of_edges()}")  # doctest: +SKIP
        """
        return self.backend.get_call_graph()

    def get_call_graph_json(self) -> str:
        """Return the call graph as a JSON string.

        Returns:
            str: JSON representation of the call graph.

        Examples:
            >>> ga = GoAnalysis(
            ...     project_dir='path/to/go/project',
            ...     analysis_level='call_graph'
            ... )
            >>> cg_json = ga.get_call_graph_json()  # doctest: +SKIP
        """
        return self.backend.get_call_graph_json()

    def get_imports(self) -> List[str]:
        """Return all import paths used across all packages.

        Returns:
            List[str]: List of unique import paths.

        Examples:
            >>> ga = GoAnalysis(project_dir='path/to/go/project')
            >>> imports = ga.get_imports()  # doctest: +SKIP
        """
        symbol_table = self.get_symbol_table()
        import_paths = set()

        for pkg in symbol_table.values():
            for imp in pkg.imports:
                import_paths.add(imp.path)

        return sorted(list(import_paths))

    def get_exported_functions(self, package: Optional[str] = None) -> Dict[str, GoCallableDecl]:
        """Return only exported (public) functions/methods.

        Args:
            package (str | None): Package path to filter by. If None, returns from all packages.

        Returns:
            Dict[str, GoCallableDecl]: Exported functions keyed by qualified name.

        Examples:
            >>> ga = GoAnalysis(project_dir='path/to/go/project')
            >>> exported = ga.get_exported_functions()  # doctest: +SKIP
        """
        all_functions = self.get_functions(package=package)
        return {name: func for name, func in all_functions.items() if func.exported}

    def get_exported_types(self, package: Optional[str] = None) -> Dict[str, GoTypeDecl]:
        """Return only exported (public) type declarations.

        Args:
            package (str | None): Package path to filter by. If None, returns from all packages.

        Returns:
            Dict[str, GoTypeDecl]: Exported types keyed by qualified name.

        Examples:
            >>> ga = GoAnalysis(project_dir='path/to/go/project')
            >>> exported_types = ga.get_exported_types()  # doctest: +SKIP
        """
        all_types = self.get_types(package=package)
        return {name: type_decl for name, type_decl in all_types.items() if type_decl.exported}

    def get_package_by_name(self, package_name: str) -> Optional[GoPackage]:
        """Get a specific package by its name or path.

        Args:
            package_name (str): The package name or path to search for.

        Returns:
            GoPackage | None: The package if found, None otherwise.

        Examples:
            >>> ga = GoAnalysis(project_dir='path/to/go/project')
            >>> main_pkg = ga.get_package_by_name("main")  # doctest: +SKIP
        """
        symbol_table = self.get_symbol_table()

        # Try exact path match first
        if package_name in symbol_table:
            return symbol_table[package_name]

        # Try matching by package name
        for pkg in symbol_table.values():
            if pkg.name == package_name:
                return pkg

        return None

    def get_statistics(self) -> Dict[str, int]:
        """Return statistics about the analyzed Go project.

        Returns:
            Dict[str, int]: Dictionary containing counts of various code elements.

        Examples:
            >>> ga = GoAnalysis(project_dir='path/to/go/project')
            >>> stats = ga.get_statistics()  # doctest: +SKIP
            >>> print(f"Packages: {stats['packages']}, Functions: {stats['functions']}")  # doctest: +SKIP
        """
        symbol_table = self.get_symbol_table()
        stats = {
            "packages": len(symbol_table),
            "functions": 0,
            "methods": 0,
            "types": 0,
            "structs": 0,
            "interfaces": 0,
            "files": 0,
        }

        for pkg in symbol_table.values():
            stats["files"] += len(pkg.files)
            stats["functions"] += len(pkg.callable_declarations)
            stats["types"] += len(pkg.type_declarations)

            for type_decl in pkg.type_declarations.values():
                if type_decl.kind == "struct":
                    stats["structs"] += 1
                elif type_decl.kind == "interface":
                    stats["interfaces"] += 1
                stats["methods"] += len(type_decl.methods)

        return stats

    # ──────────────────────────────────────────────────────────────────────────
    # PDG / SDG helpers
    # ──────────────────────────────────────────────────────────────────────────

    def get_pdg(
        self,
        package: Optional[str] = None,
        function: Optional[str] = None,
    ) -> Union[GoCLDKPDG, GoPackagePDG, GoFunctionPDG, None]:
        """Return the PDG for the entire app, a specific package, or a specific function.

        Args:
            package (str | None): Package path to filter by.
            function (str | None): Function name to filter by (requires package).

        Returns:
            GoCLDKPDG | GoPackagePDG | GoFunctionPDG | None
        """
        app = self.get_application_view()
        if app.pdg is None:
            return None

        if package is None:
            return app.pdg

        pkg_pdg = app.pdg.packages.get(package)
        if pkg_pdg is None:
            return None

        if function is None:
            return pkg_pdg

        return pkg_pdg.functions.get(function)

    def get_sdg(
        self,
        caller_package: Optional[str] = None,
    ) -> Union[GoCLDKSDG, GoPackageSDG, None]:
        """Return the SDG for the entire app, or outgoing edges for a specific package.

        Args:
            caller_package (str | None): Package path to filter by.

        Returns:
            GoCLDKSDG | GoPackageSDG | None
        """
        app = self.get_application_view()
        if app.sdg is None:
            return None

        if caller_package is None:
            return app.sdg

        return app.sdg.packages.get(caller_package)

    def get_compact_view(self) -> Dict:
        """Return the compact analysis data as a raw dictionary.

        Delegates to the backend's compact analysis. Only available when
        the GoAnalysis was initialized with compact=True.

        Returns:
            Dict: The raw compact JSON data.
        """
        return self.backend.get_compact_view()
