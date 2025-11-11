import asyncio

user_host = '127.0.0.1'
user_port = 0
developers = {}
user_name = ""


async def broadcast(msg):
    for nickname, (_, writer) in developers.items():
        writer.write(msg.encode('utf-8'))
        await writer.drain()


async def read_peer(nickname, reader):
    """Continuously read messages from a connected peer."""
    try:
        while True:
            data = await reader.readline()
            if not data:
                break
            print(f"{nickname}: {data.decode().strip()}")
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
        print(f"Connected to {nickname}")

        # Start listening to the connected peer
        asyncio.create_task(read_peer(nickname, reader))

    while True:
        user_msg = await loop.run_in_executor(None, input)
        nickname, _, msg = user_msg.partition(' ')
        msg += '\n'

        if nickname == '@broadcast':
            await broadcast(msg)

        elif nickname == '@connect':
            dev_host, dev_port = msg.split()
            await connect(dev_host, int(dev_port))

        elif nickname in developers:
            _, writer = developers[nickname]
            writer.write(msg.encode('utf-8'))
            await writer.drain()
        else:
            print("Developer Not Found")


async def handle_developer(reader, writer):
    """Handle an incoming connection."""
    addr = writer.get_extra_info('peername')
    nickname = await reader.readline()
    nickname = nickname.decode('utf-8').strip()
    developers[nickname] = (reader, writer)
    print(f"Connected to {nickname} from {addr}")

    # Send back our username for identification
    writer.write(f"{user_name}\n".encode('utf-8'))
    await writer.drain()

    try:
        while True:
            data = await reader.readline()
            if not data:
                break
            msg = data.decode('utf-8').strip()
            print(f"{nickname}: {msg}")
    except ConnectionResetError:
        pass
    finally:
        print(f"Disconnected {nickname}")
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