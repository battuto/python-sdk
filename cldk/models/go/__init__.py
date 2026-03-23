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

"""Go models package for CLDK."""

from cldk.models.go.models import (
    GoAnalysis,
    GoCallGraph,
    GoCallGraphEdge,
    GoCallGraphNode,
    GoCallableDecl,
    GoField,
    GoImport,
    GoIssue,
    GoMetadata,
    GoPackage,
    GoParameter,
    GoPosition,
    GoResult,
    GoSymbolTable,
    GoTypeDecl,
    # PDG models
    GoPDGPosition,
    GoPDGNode,
    GoPDGDataEdge,
    GoPDGCtrlEdge,
    GoFunctionPDG,
    GoPackagePDG,
    GoCLDKPDG,
    # SDG models
    GoSDGInterEdge,
    GoPackageSDG,
    GoCLDKSDG,
    # Compact models
    CompactGoPackagePDG,
    CompactGoPDG,
    CompactGoPackageSDG,
    CompactGoSDG,
)

__all__ = [
    "GoAnalysis",
    "GoCallGraph",
    "GoCallGraphEdge",
    "GoCallGraphNode",
    "GoCallableDecl",
    "GoField",
    "GoImport",
    "GoIssue",
    "GoMetadata",
    "GoPackage",
    "GoParameter",
    "GoPosition",
    "GoResult",
    "GoSymbolTable",
    "GoTypeDecl",
    # PDG
    "GoPDGPosition",
    "GoPDGNode",
    "GoPDGDataEdge",
    "GoPDGCtrlEdge",
    "GoFunctionPDG",
    "GoPackagePDG",
    "GoCLDKPDG",
    # SDG
    "GoSDGInterEdge",
    "GoPackageSDG",
    "GoCLDKSDG",
    # Compact
    "CompactGoPackagePDG",
    "CompactGoPDG",
    "CompactGoPackageSDG",
    "CompactGoSDG",
]

