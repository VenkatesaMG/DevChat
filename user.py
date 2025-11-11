import asyncio
from rich.console import Console
from rich.text import Text
from rich.align import Align
import shutil

user_host = '127.0.0.1'
user_port = 0
developers = {}
user_name = ""
console = Console()
terminal_width = shutil.get_terminal_size().columns

async def run_command(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE
    )

    stdout, stderr = await proc.communicate()
    if stdout:
        print(f"[stdout]\n{stdout.decode()}")
    elif stderr:
        print(f"[stderr]\n{stderr.decode()}")

async def broadcast(msg):
    for nickname, (_, writer) in developers.items():
        writer.write(msg.encode('utf-8'))
        await writer.drain()

def custom_print(nickname, msg):
    formatted = f"[cyan]{nickname}[/cyan]\n {msg}"
    console.print(formatted, justify="right")

async def read_peer(nickname, reader):
    """Continuously read messages from a connected peer."""
    try:
        while True:
            data = await reader.readline()
            if not data:
                break
            custom_print(nickname, data.decode().strip())
    except ConnectionResetError:
        pass
    finally:
        print(f"Connection to {nickname} closed")
        del developers[nickname]

async def user_input():
    loop = asyncio.get_event_loop()

    async def connect(host, port):
        reader, writer = await asyncio.open_connection(host, port)
        writer.write(f"{user_name}\n".encode('utf-8'))
        await writer.drain()

        nickname = await reader.readline()
        nickname = nickname.decode('utf-8').strip()
        developers[nickname] = (reader, writer)

        console.print(f"[black on #00fd4c] Connected [/] {nickname}")
        asyncio.create_task(read_peer(nickname, reader))

    while True:
        user_msg = await loop.run_in_executor(None, input)
        print("\033[K\033[F\033[K", end="")  # clear the prompt
        nickname, _, msg = user_msg.partition(' ')
        msg += '\n'
        if nickname == '@broadcast':
            console.print(f"[yellow]{user_name}[/yellow]\n [#39418f]{nickname}[/#39418f] {msg}")
            await broadcast(msg)
        elif nickname == '@connect':
            console.print(f"[yellow]{user_name}[/yellow]\n [#39418f]{nickname}[/#39418f] {msg}")
            dev_host, dev_port = msg.strip().split()
            await connect(dev_host, int(dev_port))
        elif nickname == '@term':
            console.print(f"[yellow]{user_name}[/yellow]\n [#39418f]{nickname}[/#39418f] {msg}")
            msg = msg.strip()
            await asyncio.create_task(run_command(msg))
        elif nickname in developers:
            console.print(f"[yellow]{user_name}[/yellow]\n @[cyan]{nickname}[/cyan] {msg}")
            _, writer = developers[nickname]
            writer.write(msg.encode('utf-8'))
            await writer.drain()
        else:
            console.print("[#ff605e]Developer Not Found[/#ff605e]")

async def handle_developer(reader, writer):

    """Handle an incoming connection."""
    addr = writer.get_extra_info('peername')
    nickname = await reader.readline()
    nickname = nickname.decode('utf-8').strip()
    developers[nickname] = (reader, writer)
    console.print(f"[black on #00fd4c] Connected [/] {nickname}")

    # Send back our username for identification
    writer.write(f"{user_name}\n".encode('utf-8'))
    await writer.drain()

    try:
        while True:
            data = await reader.readline()
            if not data:
                break
            msg = data.decode('utf-8').strip()
            custom_print(nickname, msg)
    except ConnectionResetError:
        pass
    finally:
        console.print(f"[black on #e9535d]Disconnected[/black on #e9535d] {nickname}")
        del developers[nickname]
        writer.close()
        await writer.wait_closed()

async def main():
    global user_name
    user_name = input("Username: ")

    server = await asyncio.start_server(handle_developer, user_host, user_port)
    host, port = server.sockets[0].getsockname()
    print(f"Server running on {host}:{port}")

    async with server:
        await asyncio.gather(server.serve_forever(), user_input())

asyncio.run(main())