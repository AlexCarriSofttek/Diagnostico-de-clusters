def bytes2mi(bytes_value): 
    return bytes_value / (1024 * 1024)

def bytes2gi(bytes_value: float) -> float:
    return bytes_value / (1024 ** 3)

def cpu2millicores(cpu):
    if cpu.endswith("m"):
        return int(cpu.replace("m", ""))
    return int(cpu) * 1000

def mb2mi(mb: float) -> float:
    return mb * 1_000_000 / 1_048_576

