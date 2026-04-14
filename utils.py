def bytes2mi(bytes_value): 
    if bytes_value is None:
            return 0.0

    return bytes_value / (1024 * 1024)


def cpu_to_millicores(cpu):
    if cpu is None:
        return 0
    if cpu.endswith("m"):
        return int(cpu.replace("m", ""))
    return int(cpu) * 1000

