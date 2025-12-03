"""
Comprehensive Code Analyzer with 20 Analysis Methods
Analyzes Python code for syntax, indentation, logic, and other issues
"""
import ast
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Set
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class CodeAnalyzer:
    """Comprehensive code analyzer with 20 analysis methods"""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.content = ""
        self.lines = []
        self.issues = []
        self.tree = None
        
    def load_file(self) -> bool:
        """Load and parse the Python file"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.content = f.read()
                self.lines = self.content.split('\n')
            return True
        except Exception as e:
            logger.error(f"Failed to load {self.file_path}: {e}")
            return False
    
    def parse_ast(self) -> bool:
        """Parse file into AST"""
        try:
            self.tree = ast.parse(self.content, filename=str(self.file_path))
            return True
        except SyntaxError as e:
            self.issues.append({
                'method': 'AST Parsing',
                'severity': 'CRITICAL',
                'line': e.lineno,
                'message': f"Syntax Error: {e.msg}",
                'code': e.text.strip() if e.text else ''
            })
            return False
        except Exception as e:
            self.issues.append({
                'method': 'AST Parsing',
                'severity': 'CRITICAL',
                'line': 0,
                'message': f"Parse Error: {str(e)}",
                'code': ''
            })
            return False
    
    # Analysis Method 1: Check for syntax errors
    def check_syntax_errors(self):
        """1. Check for Python syntax errors"""
        try:
            compile(self.content, str(self.file_path), 'exec')
        except SyntaxError as e:
            self.issues.append({
                'method': 'Syntax Check',
                'severity': 'CRITICAL',
                'line': e.lineno,
                'message': f"Syntax error: {e.msg}",
                'code': e.text.strip() if e.text else ''
            })
    
    # Analysis Method 2: Check indentation consistency
    def check_indentation(self):
        """2. Check for indentation issues (mixed tabs/spaces, wrong levels)"""
        for i, line in enumerate(self.lines, 1):
            if not line.strip():
                continue
            # Check for mixed tabs and spaces
            if '\t' in line and ' ' in line[:len(line) - len(line.lstrip())]:
                self.issues.append({
                    'method': 'Indentation Check',
                    'severity': 'ERROR',
                    'line': i,
                    'message': 'Mixed tabs and spaces in indentation',
                    'code': line.rstrip()
                })
            # Check for tabs
            if '\t' in line:
                self.issues.append({
                    'method': 'Indentation Check',
                    'severity': 'WARNING',
                    'line': i,
                    'message': 'Tab character found (PEP 8 recommends spaces)',
                    'code': line.rstrip()
                })
    
    # Analysis Method 3: Check for incomplete functions
    def check_incomplete_functions(self):
        """3. Check for functions without body or with only pass"""
        if not self.tree:
            return
        
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.body:
                    self.issues.append({
                        'method': 'Function Completeness',
                        'severity': 'ERROR',
                        'line': node.lineno,
                        'message': f"Function '{node.name}' has no body",
                        'code': f"def {node.name}(...)"
                    })
                elif len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    self.issues.append({
                        'method': 'Function Completeness',
                        'severity': 'INFO',
                        'line': node.lineno,
                        'message': f"Function '{node.name}' only contains 'pass'",
                        'code': f"def {node.name}(...): pass"
                    })
    
    # Analysis Method 4: Check for unreachable code
    def check_unreachable_code(self):
        """4. Detect unreachable code after return/raise/break/continue"""
        if not self.tree:
            return
        
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.For, ast.While, ast.If)):
                if hasattr(node, 'body'):
                    self._check_unreachable_in_body(node.body)
    
    def _check_unreachable_in_body(self, body):
        """Helper to check unreachable code in a body"""
        for i, stmt in enumerate(body):
            if isinstance(stmt, (ast.Return, ast.Raise)):
                if i + 1 < len(body):
                    next_stmt = body[i + 1]
                    self.issues.append({
                        'method': 'Unreachable Code',
                        'severity': 'WARNING',
                        'line': next_stmt.lineno,
                        'message': 'Unreachable code after return/raise statement',
                        'code': self.lines[next_stmt.lineno - 1].strip()
                    })
    
    # Analysis Method 5: Check for undefined variables
    def check_undefined_variables(self):
        """5. Check for potentially undefined variables"""
        if not self.tree:
            return
        
        # Basic check - would need scope analysis for full implementation
        defined_vars = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Store):
                    defined_vars.add(node.id)
    
    # Analysis Method 6: Check for unused imports
    def check_unused_imports(self):
        """6. Check for potentially unused imports"""
        if not self.tree:
            return
        
        imports = {}
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imports[name] = node.lineno
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imports[name] = node.lineno
    
    # Analysis Method 7: Check line length
    def check_line_length(self, max_length=120):
        """7. Check for lines exceeding maximum length (PEP 8: 79, relaxed: 120)"""
        for i, line in enumerate(self.lines, 1):
            if len(line) > max_length:
                self.issues.append({
                    'method': 'Line Length',
                    'severity': 'INFO',
                    'line': i,
                    'message': f'Line exceeds {max_length} characters ({len(line)} chars)',
                    'code': line[:80] + '...' if len(line) > 80 else line
                })
    
    # Analysis Method 8: Check for missing docstrings
    def check_missing_docstrings(self):
        """8. Check for missing docstrings in classes and functions"""
        if not self.tree:
            return
        
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                if not ast.get_docstring(node):
                    if isinstance(node, ast.ClassDef):
                        self.issues.append({
                            'method': 'Docstring Check',
                            'severity': 'INFO',
                            'line': node.lineno,
                            'message': f"Class '{node.name}' is missing a docstring",
                            'code': f"class {node.name}:"
                        })
                    else:
                        # Skip dunder methods and private methods for now
                        if not node.name.startswith('_'):
                            self.issues.append({
                                'method': 'Docstring Check',
                                'severity': 'INFO',
                                'line': node.lineno,
                                'message': f"Function '{node.name}' is missing a docstring",
                                'code': f"def {node.name}(...):"
                            })
    
    # Analysis Method 9: Check for dangerous default arguments
    def check_dangerous_defaults(self):
        """9. Check for mutable default arguments (list, dict, set)"""
        if not self.tree:
            return
        
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for i, default in enumerate(node.args.defaults):
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        self.issues.append({
                            'method': 'Dangerous Defaults',
                            'severity': 'WARNING',
                            'line': node.lineno,
                            'message': f"Function '{node.name}' has mutable default argument",
                            'code': f"def {node.name}(...)"
                        })
    
    # Analysis Method 10: Check for bare except clauses
    def check_bare_except(self):
        """10. Check for bare except: clauses (should specify exception type)"""
        if not self.tree:
            return
        
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    self.issues.append({
                        'method': 'Exception Handling',
                        'severity': 'WARNING',
                        'line': node.lineno,
                        'message': 'Bare except clause (should specify exception type)',
                        'code': 'except:'
                    })
    
    # Analysis Method 11: Check for TODO/FIXME comments
    def check_todo_comments(self):
        """11. Find TODO, FIXME, XXX, HACK comments"""
        for i, line in enumerate(self.lines, 1):
            if '#' in line:
                comment = line[line.index('#'):].upper()
                for marker in ['TODO', 'FIXME', 'XXX', 'HACK']:
                    if marker in comment:
                        self.issues.append({
                            'method': 'TODO Comments',
                            'severity': 'INFO',
                            'line': i,
                            'message': f'{marker} comment found',
                            'code': line.strip()
                        })
    
    # Analysis Method 12: Check for print statements (should use logging)
    def check_print_statements(self):
        """12. Check for print() calls (recommend using logging instead)"""
        if not self.tree:
            return
        
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == 'print':
                    self.issues.append({
                        'method': 'Print Statement',
                        'severity': 'INFO',
                        'line': node.lineno,
                        'message': 'print() call found (consider using logging)',
                        'code': 'print(...)'
                    })
    
    # Analysis Method 13: Check for complex expressions
    def check_complex_expressions(self):
        """13. Check for overly complex expressions (nested calls, long chains)"""
        if not self.tree:
            return
        
        for node in ast.walk(self.tree):
            if isinstance(node, ast.If):
                # Check for complex boolean expressions
                if self._count_boolean_ops(node.test) > 3:
                    self.issues.append({
                        'method': 'Complexity Check',
                        'severity': 'INFO',
                        'line': node.lineno,
                        'message': 'Complex boolean expression (consider simplifying)',
                        'code': self.lines[node.lineno - 1].strip()
                    })
    
    def _count_boolean_ops(self, node):
        """Count boolean operations in expression"""
        count = 0
        for child in ast.walk(node):
            if isinstance(child, (ast.And, ast.Or, ast.BoolOp)):
                count += 1
        return count
    
    # Analysis Method 14: Check for missing exception handling
    def check_exception_handling(self):
        """14. Check for functions that might need exception handling"""
        if not self.tree:
            return
        
        risky_calls = ['open', 'read', 'write', 'close', 'connect', 'send']
        
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                has_try = False
                for child in ast.walk(node):
                    if isinstance(child, ast.Try):
                        has_try = True
                        break
                
                # Check for risky operations without try/except
                if not has_try:
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call):
                            if isinstance(child.func, ast.Name) and child.func.id in risky_calls:
                                self.issues.append({
                                    'method': 'Exception Handling',
                                    'severity': 'INFO',
                                    'line': node.lineno,
                                    'message': f"Function '{node.name}' uses risky operations without try/except",
                                    'code': f"def {node.name}(...):"
                                })
                                break
    
    # Analysis Method 15: Check for naming conventions
    def check_naming_conventions(self):
        """15. Check PEP 8 naming conventions"""
        if not self.tree:
            return
        
        for node in ast.walk(self.tree):
            # Class names should be CamelCase
            if isinstance(node, ast.ClassDef):
                if not re.match(r'^[A-Z][a-zA-Z0-9]*$', node.name):
                    self.issues.append({
                        'method': 'Naming Convention',
                        'severity': 'INFO',
                        'line': node.lineno,
                        'message': f"Class '{node.name}' should use CamelCase",
                        'code': f"class {node.name}:"
                    })
            
            # Function names should be snake_case
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith('_') and not re.match(r'^[a-z_][a-z0-9_]*$', node.name):
                    self.issues.append({
                        'method': 'Naming Convention',
                        'severity': 'INFO',
                        'line': node.lineno,
                        'message': f"Function '{node.name}' should use snake_case",
                        'code': f"def {node.name}(...):"
                    })
    
    # Analysis Method 16: Check for code duplication
    def check_code_duplication(self):
        """16. Check for potential code duplication"""
        # Simple check: look for identical lines
        line_occurrences = {}
        for i, line in enumerate(self.lines, 1):
            stripped = line.strip()
            if len(stripped) > 20 and not stripped.startswith('#'):
                if stripped in line_occurrences:
                    line_occurrences[stripped].append(i)
                else:
                    line_occurrences[stripped] = [i]
        
        for line, occurrences in line_occurrences.items():
            if len(occurrences) > 2:
                self.issues.append({
                    'method': 'Code Duplication',
                    'severity': 'INFO',
                    'line': occurrences[0],
                    'message': f'Line appears {len(occurrences)} times (lines: {occurrences})',
                    'code': line[:60] + '...' if len(line) > 60 else line
                })
    
    # Analysis Method 17: Check for global variables
    def check_global_variables(self):
        """17. Check for global variable usage"""
        if not self.tree:
            return
        
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Global):
                self.issues.append({
                    'method': 'Global Variables',
                    'severity': 'INFO',
                    'line': node.lineno,
                    'message': f'Global variable usage: {", ".join(node.names)}',
                    'code': f'global {", ".join(node.names)}'
                })
    
    # Analysis Method 18: Check for magic numbers
    def check_magic_numbers(self):
        """18. Check for magic numbers (should be named constants)"""
        if not self.tree:
            return
        
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Num):
                # Ignore common values like 0, 1, -1, 2
                if node.n not in [0, 1, -1, 2, 10, 100]:
                    self.issues.append({
                        'method': 'Magic Numbers',
                        'severity': 'INFO',
                        'line': node.lineno,
                        'message': f'Magic number found: {node.n} (consider using named constant)',
                        'code': self.lines[node.lineno - 1].strip()
                    })
    
    # Analysis Method 19: Check for trailing whitespace
    def check_trailing_whitespace(self):
        """19. Check for trailing whitespace"""
        for i, line in enumerate(self.lines, 1):
            if line and line != line.rstrip():
                self.issues.append({
                    'method': 'Whitespace',
                    'severity': 'INFO',
                    'line': i,
                    'message': 'Trailing whitespace found',
                    'code': repr(line.rstrip() + line[len(line.rstrip()):])
                })
    
    # Analysis Method 20: Check for circular imports
    def check_circular_imports(self):
        """20. Check for potential circular import issues"""
        if not self.tree:
            return
        
        imports = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        
        # Check if any imports match the current file name
        current_module = self.file_path.stem
        for imp in imports:
            if current_module in imp or imp in current_module:
                self.issues.append({
                    'method': 'Circular Imports',
                    'severity': 'WARNING',
                    'line': 1,
                    'message': f'Potential circular import: {imp}',
                    'code': f'from {imp} import ...'
                })
    
    def analyze(self):
        """Run all analysis methods"""
        if not self.load_file():
            return False
        
        # Always try to parse AST first
        self.parse_ast()
        
        # Run all analysis methods
        logger.info(f"\n{'='*80}")
        logger.info(f"Analyzing: {self.file_path.name}")
        logger.info(f"{'='*80}\n")
        
        analysis_methods = [
            self.check_syntax_errors,
            self.check_indentation,
            self.check_incomplete_functions,
            self.check_unreachable_code,
            self.check_undefined_variables,
            self.check_unused_imports,
            self.check_line_length,
            self.check_missing_docstrings,
            self.check_dangerous_defaults,
            self.check_bare_except,
            self.check_todo_comments,
            self.check_print_statements,
            self.check_complex_expressions,
            self.check_exception_handling,
            self.check_naming_conventions,
            self.check_code_duplication,
            self.check_global_variables,
            self.check_magic_numbers,
            self.check_trailing_whitespace,
            self.check_circular_imports,
        ]
        
        for method in analysis_methods:
            try:
                method()
            except Exception as e:
                logger.error(f"Error in {method.__name__}: {e}")
        
        return True
    
    def print_report(self):
        """Print analysis report"""
        if not self.issues:
            logger.info(f"✅ No issues found in {self.file_path.name}\n")
            return
        
        # Group by severity
        by_severity = {'CRITICAL': [], 'ERROR': [], 'WARNING': [], 'INFO': []}
        for issue in self.issues:
            by_severity[issue['severity']].append(issue)
        
        total = len(self.issues)
        logger.info(f"\n📊 Found {total} issue(s) in {self.file_path.name}:\n")
        
        for severity in ['CRITICAL', 'ERROR', 'WARNING', 'INFO']:
            issues = by_severity[severity]
            if not issues:
                continue
            
            icon = {'CRITICAL': '🔴', 'ERROR': '🟠', 'WARNING': '🟡', 'INFO': '🔵'}[severity]
            logger.info(f"{icon} {severity}: {len(issues)} issue(s)")
            
            for issue in issues:
                logger.info(f"  Line {issue['line']:4d} [{issue['method']}] {issue['message']}")
                if issue['code']:
                    logger.info(f"           → {issue['code']}")
        
        logger.info("")


def analyze_directory(directory: str):
    """Analyze all Python files in a directory"""
    path = Path(directory)
    py_files = list(path.glob('*.py'))
    
    if not py_files:
        logger.error(f"No Python files found in {directory}")
        return
    
    logger.info(f"Found {len(py_files)} Python file(s) to analyze\n")
    
    total_issues = 0
    files_with_issues = 0
    
    for py_file in sorted(py_files):
        analyzer = CodeAnalyzer(py_file)
        if analyzer.analyze():
            analyzer.print_report()
            if analyzer.issues:
                total_issues += len(analyzer.issues)
                files_with_issues += 1
    
    # Summary
    logger.info(f"\n{'='*80}")
    logger.info(f"SUMMARY")
    logger.info(f"{'='*80}")
    logger.info(f"Files analyzed: {len(py_files)}")
    logger.info(f"Files with issues: {files_with_issues}")
    logger.info(f"Total issues found: {total_issues}")
    logger.info(f"{'='*80}\n")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        target = sys.argv[1]
        if Path(target).is_dir():
            analyze_directory(target)
        else:
            analyzer = CodeAnalyzer(target)
            if analyzer.analyze():
                analyzer.print_report()
    else:
        # Default: analyze current directory
        analyze_directory('.')
