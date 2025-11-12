import asyncio
from rich.console import Console
from rich.text import Text
from rich.align import Align
import shutil
from datetime import datetime
import os
from rich.tree import Tree
import inspect

DNS_IP = '127.0.0.1'
DNS_PORT = 8080

user_host = '127.0.0.1'
user_port = 0
developers = {}
user_name = ""
console = Console()
terminal_width = shutil.get_terminal_size().columns
LOG_DIR = 'devchats/logs'
os.makedirs(LOG_DIR, exist_ok=True)

def log_messages(sender, message):
    log_path = os.path.join(LOG_DIR, f"{user_name}.log")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, "a+", encoding = 'utf-8') as file:
        file.write(f"{timestamp} {sender} {message}")

async def register_with_dns(username, addr):
    packet = f"INS\tDNS/0.1\r\n{username}\t{addr}\r\n\r\n"
    reader, writer = await asyncio.open_connection(DNS_IP, DNS_PORT)
    writer.write(packet.encode('utf-8'))
    await writer.drain()
    response = await reader.read(1024)
    print("Register response:", response.decode().strip())
    writer.close()
    await writer.wait_closed()

async def dns_resolve(name):
    packet = f"RES\tDNS/0.1\r\n{name}\taddress\r\n\r\n"
    reader, writer = await asyncio.open_connection(DNS_IP, DNS_PORT)
    writer.write(packet.encode('utf-8'))
    await writer.drain()
    response = await reader.read(1024)
    print("Resolve response:", response.decode().strip())
    writer.close()
    await writer.wait_closed()

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

def history():
    log_path = f"{LOG_DIR}/{user_name}.log"
    if os.path.exists(log_path):
        print(log_path)
        with open(log_path, "r", encoding='utf-8') as file:
            messages = file.read()
        print(messages)

def show_connected_developers():
    tree = Tree("[bold cyan]Connected Developers[/bold cyan]")
    for name, (reader, writer) in developers.items():
        addr = writer.get_extra_info('peername')
        tree.add(f"[green]{name}[/green] ([italic]{addr[0]}:{addr[1]}[/italic])")
    console.print(tree)

async def read_peer(nickname, reader):
    """Continuously read messages from a connected peer."""
    try:
        while True:
            data = await reader.readline()
            if not data:
                break
            data = data.decode()
            custom_print(nickname, data)
            log_messages(nickname, data)
    except ConnectionResetError:
        pass
    finally:
        print(f"Connection to {nickname} closed")
        del developers[nickname]

async def connect(msg):
        host, port = msg.strip().split()
        port = int(port)
        reader, writer = await asyncio.open_connection(host, port)
        writer.write(f"{user_name}\n".encode('utf-8'))
        await writer.drain()

        nickname = await reader.readline()
        nickname = nickname.decode('utf-8').strip()
        developers[nickname] = (reader, writer)

        console.print(f"[black on #00fd4c] Connected [/] {nickname}")
        asyncio.create_task(read_peer(nickname, reader))

async def user_input():
    loop = asyncio.get_event_loop()

    while True:
        user_msg = await loop.run_in_executor(None, input)
        print("\033[K\033[F\033[K", end="")  # clear the prompt
        nickname, _, msg = user_msg.partition(' ')
        msg += '\n'
        if nickname in commands:
            console.print(f"[yellow]{user_name}[/yellow]\n [#39418f]{nickname}[/#39418f] {msg}")
            if len(inspect.signature(commands[nickname]).parameters) == 0:
                commands[nickname]()
            elif nickname in commands:
                await commands[nickname](msg)
        elif nickname in developers:
            console.print(f"[yellow]{user_name}[/yellow]\n @[cyan]{nickname}[/cyan] {msg}")
            log_messages(user_name, msg)
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

    asyncio.create_task(read_peer(nickname, reader))
    # try:
    #     while True:
    #         data = await reader.readline()
    #         if not data:
    #             break
    #         msg = data.decode('utf-8').strip()
    #         custom_print(nickname, msg)
    # except ConnectionResetError:
    #     pass
    # finally:
    #     console.print(f"[black on #e9535d]Disconnected[/black on #e9535d] {nickname}")
    #     del developers[nickname]
    #     writer.close()
    #     await writer.wait_closed()

commands = {
    '@broadcast':broadcast,
    '@connect' : connect,
    '@term' : run_command,
    '@history' : history,
    '@show' : show_connected_developers,
    '@dns_resolve' : dns_resolve,
    }

async def main():
    global user_name
    user_name = input("Username: ")

    server = await asyncio.start_server(handle_developer, user_host, user_port)
    host, port = server.sockets[0].getsockname()
    print(f"Server running on {host}:{port}")

    await register_with_dns(user_name, f"{host}:{port}")

    async with server:
        await asyncio.gather(server.serve_forever(), user_input())

asyncio.run(main())