import ast

def find_sync_awaits(filename):
    with open(filename, 'r') as f:
        tree = ast.parse(f.read())
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for child in ast.walk(node):
                if isinstance(child, ast.Await):
                    print(f"Sync function {node.name} has await at line {child.lineno}")

find_sync_awaits('ark_learning_agent/frontend_api.py')
