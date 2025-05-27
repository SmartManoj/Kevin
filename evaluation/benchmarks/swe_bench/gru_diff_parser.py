from pyperclip import paste

a = paste()

print(eval(a.split('":', 1)[-1].strip()[:-1]))
