import psutil

def list_network_connections():
    print(f"{'Proto':<6} {'Local Address':<25} {'Remote Address':<25} {'Status':<13} {'PID':<8} {'Process Name'}")
    print("-" * 90)

    for conn in psutil.net_connections(kind='inet'):
        laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else ""
        raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else ""
        pid = conn.pid or "-"
        proc_name = "-"
        try:
            if conn.pid:
                proc = psutil.Process(conn.pid)
                proc_name = proc.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        proto = "TCP" if conn.type == psutil.SOCK_STREAM else "UDP"
        print(f"{proto:<6} {laddr:<25} {raddr:<25} {conn.status:<13} {pid:<8} {proc_name}")

if __name__ == "__main__":
    list_network_connections()
