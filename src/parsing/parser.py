import ast


expr = """
def function1(parameter):
    " documentation "
    function3(parameter)
    new_parameter = function4(parameter)
    return function2(new_parameter)
    
def function2(parameter2):
    return parameter2
    
def function3(parameter3):
    print(parameter3)
    
def function4(parameter4):
    return parameter4
"""

parsed = ast.parse(expr)
print(parsed._fields)

function1 = parsed.body[0]

print(function1._fields)
print(function1.body)



