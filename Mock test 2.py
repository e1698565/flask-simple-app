def triange(rows):
    res = []
    for i in range(1, rows//2+2):
        spaces = ' ' * (rows -i)
        stars = '*' * (2 *i -1)
        res.append(spaces + stars + spaces)

    return res

def rhombus(rows, chars):
    res = []
    for i in range(1, rows//2+2):
        spaces = ' ' * (rows -i)
        stars = ((chars + "-") * (i)) [:-1]
        res.append(spaces + stars + spaces)

    for i in range(rows//2+2,0, -1):
        spaces = ' ' * (rows -i)
        stars = ((chars + "-") * (i)) [:-1]
        res.append(spaces + stars + spaces)

    return res

print("\n".join(rhombus(7,"$")))
    


