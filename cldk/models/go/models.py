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

"""
Go models module for representing Go code analysis structures.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GoPosition(BaseModel):
    """Represents a position in Go source code.

    Attributes:
        file (str): The file path.
        start_line (int): The starting line number (1-indexed).
        start_column (int): The starting column number (1-indexed).
        end_line (int): The ending line number (1-indexed), optional.
        end_column (int): The ending column number (1-indexed), optional.
    """

    file: str
    start_line: int
    start_column: int
    end_line: Optional[int] = None
    end_column: Optional[int] = None


class GoImport(BaseModel):
    """Represents a Go import statement.

    Attributes:
        path (str): The import path (e.g., "fmt", "github.com/user/repo").
        alias (str): The import alias, if any.
        position (GoPosition): The position of the import in the source code.
    """

    path: str
    alias: Optional[str] = None
    position: Optional[GoPosition] = None


class GoField(BaseModel):
    """Represents a field in a Go struct.

    Attributes:
        name (str): The field name.
        type (str): The field type.
        position (GoPosition): The position of the field in the source code.
        exported (bool): Whether the field is exported (capitalized).
        embedded (bool): Whether the field is an embedded type.
        tag (str): The struct tag, if any.
        documentation (str): The documentation comment for the field.
    """

    name: str
    type: str
    position: Optional[GoPosition] = None
    exported: bool = False
    embedded: bool = False
    tag: Optional[str] = None
    documentation: Optional[str] = None


class GoParameter(BaseModel):
    """Represents a parameter in a Go function/method signature.

    Attributes:
        name (str): The parameter name.
        type (str): The parameter type.
    """

    name: str
    type: str


class GoResult(BaseModel):
    """Represents a return value in a Go function/method signature.

    Attributes:
        name (str): The return value name (may be empty for unnamed returns).
        type (str): The return value type.
    """

    name: Optional[str] = None
    type: str


class GoCallableDecl(BaseModel):
    """Represents a callable declaration (function or method) in Go.

    Attributes:
        qualified_name (str): The fully qualified name (e.g., "package.Receiver.Method").
        name (str): The simple name of the callable.
        signature (str): The full signature string.
        kind (str): The kind of callable ("function" or "method").
        receiver_type (str): For methods, the receiver type name.
        parameters (List[GoParameter]): The function/method parameters.
        results (List[GoResult]): The function/method return values.
        position (GoPosition): The position of the callable in the source code.
        documentation (str): The documentation comment for the callable.
        exported (bool): Whether the callable is exported.
    """

    qualified_name: str
    name: str
    signature: str
    kind: str  # "function" or "method"
    receiver_type: Optional[str] = None
    parameters: List[GoParameter] = Field(default_factory=list)
    results: List[GoResult] = Field(default_factory=list)
    position: Optional[GoPosition] = None
    documentation: Optional[str] = None
    exported: bool = False


class GoTypeDecl(BaseModel):
    """Represents a type declaration in Go.

    Attributes:
        qualified_name (str): The fully qualified type name (e.g., "package.TypeName").
        name (str): The simple type name.
        kind (str): The kind of type ("struct", "interface", "alias", etc.).
        position (GoPosition): The position of the type declaration in the source code.
        documentation (str): The documentation comment for the type.
        fields (List[GoField]): For structs, the list of fields.
        methods (Dict[str, GoCallableDecl]): Methods associated with this type (keyed by qualified name).
        exported (bool): Whether the type is exported.
        underlying_type (str): For type aliases, the underlying type.
    """

    qualified_name: str
    name: str
    kind: str  # "struct", "interface", "alias", etc.
    position: Optional[GoPosition] = None
    documentation: Optional[str] = None
    fields: List[GoField] = Field(default_factory=list)
    methods: Dict[str, GoCallableDecl] = Field(default_factory=dict)
    exported: bool = False
    underlying_type: Optional[str] = None


class GoPackage(BaseModel):
    """Represents a Go package.

    Attributes:
        path (str): The full package import path (e.g., "github.com/user/repo/pkg").
        name (str): The package name (e.g., "pkg").
        files (List[str]): List of source file paths in the package.
        imports (List[GoImport]): List of imports used by the package.
        type_declarations (Dict[str, GoTypeDecl]): Type declarations in the package (keyed by qualified name).
        callable_declarations (Dict[str, GoCallableDecl]): Top-level functions/methods (keyed by qualified name).
        variables (Dict[str, Any]): Global variables (simplified representation).
        constants (Dict[str, Any]): Global constants (simplified representation).
    """

    path: str
    name: str
    files: List[str] = Field(default_factory=list)
    imports: List[GoImport] = Field(default_factory=list)
    type_declarations: Dict[str, GoTypeDecl] = Field(default_factory=dict)
    callable_declarations: Dict[str, GoCallableDecl] = Field(default_factory=dict)
    variables: Dict[str, Any] = Field(default_factory=dict)
    constants: Dict[str, Any] = Field(default_factory=dict)


class GoSymbolTable(BaseModel):
    """Represents the symbol table for a Go project.

    Attributes:
        packages (Dict[str, GoPackage]): All packages in the project (keyed by package path).
    """

    packages: Dict[str, GoPackage] = Field(default_factory=dict)


class GoCallGraphNode(BaseModel):
    """Represents a node in the Go call graph.

    Attributes:
        id (str): Unique identifier for the node.
        qualified_name (str): The fully qualified name of the callable.
        package (str): The package path.
        name (str): The simple name of the callable.
        kind (str): The kind ("function" or "method").
        receiver_type (str): For methods, the receiver type.
        position (GoPosition): The position in the source code.
    """

    id: str
    qualified_name: str
    package: str
    name: str
    kind: str
    receiver_type: Optional[str] = None
    position: Optional[GoPosition] = None


class GoCallGraphEdge(BaseModel):
    """Represents an edge in the Go call graph.

    Attributes:
        source (str): The ID of the caller node.
        target (str): The ID of the callee node.
        kind (str): The kind of call ("static", "dynamic", "interface").
        position (GoPosition): The position of the call site in the source code.
    """

    source: str
    target: str
    kind: str
    position: Optional[GoPosition] = None


class GoCallGraph(BaseModel):
    """Represents the call graph for a Go project.

    Attributes:
        algorithm (str): The algorithm used to construct the call graph (e.g., "CHA", "RTA").
        nodes (List[GoCallGraphNode]): All nodes in the call graph.
        edges (List[GoCallGraphEdge]): All edges in the call graph.
    """

    algorithm: str
    nodes: List[GoCallGraphNode] = Field(default_factory=list)
    edges: List[GoCallGraphEdge] = Field(default_factory=list)


class GoMetadata(BaseModel):
    """Represents metadata about the Go analysis.

    Attributes:
        analyzer (str): The name of the analyzer (e.g., "codeanalyzer-go").
        version (str): The analyzer version.
        language (str): The language being analyzed ("go").
        analysis_level (str): The level of analysis performed.
        timestamp (str): The timestamp of the analysis.
        project_path (str): The path to the analyzed project.
        go_version (str): The Go version detected in the project.
    """

    analyzer: str
    version: str
    language: str
    analysis_level: str
    timestamp: Optional[str] = None
    project_path: Optional[str] = None
    go_version: Optional[str] = None


class GoIssue(BaseModel):
    """Represents an issue/diagnostic found during Go analysis.

    Attributes:
        severity (str): The severity level ("error", "warning", "info").
        code (str): The issue code or identifier.
        message (str): The issue message.
        file (str): The file where the issue was found.
        position (GoPosition): The position of the issue in the source code.
    """

    severity: str
    code: str
    message: str
    file: str
    position: Optional[GoPosition] = None


class GoAnalysis(BaseModel):
    """Represents the complete Go code analysis result.

    Attributes:
        metadata (GoMetadata): Metadata about the analysis.
        symbol_table (GoSymbolTable): The symbol table.
        call_graph (GoCallGraph): The call graph (if requested).
        pdg (Any): Program Dependence Graph (placeholder for future use).
        sdg (Any): System Dependence Graph (placeholder for future use).
        issues (List[GoIssue]): Issues/diagnostics found during analysis.
    """

    metadata: GoMetadata
    symbol_table: Optional[GoSymbolTable] = None
    call_graph: Optional[GoCallGraph] = None
    pdg: Optional[Any] = None
    sdg: Optional[Any] = None
    issues: List[GoIssue] = Field(default_factory=list)
