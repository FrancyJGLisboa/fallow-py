def tangled(a, b, c, d):
    if a:
        for i in range(b):
            if i % 2 == 0:
                while c > 0:
                    c -= 1
                    if c == d:
                        break
                    elif c < 0:
                        continue
            elif i % 3 == 0:
                if d:
                    return i
            else:
                pass
    return a or b or c or d
