import asyncio

DNS_RECORD = {}

async def handle_client(reader, writer):
    data = await reader.read(1024)
    message = data.decode().strip()
    print("Received:", message)

    try:
        lines = message.split('\r\n')
        request_line = lines[0].split('\t')[0]
        name, req_addr = lines[1].split('\t')
        name = name.strip()
        req_addr = req_addr.strip()
    except Exception:
        writer.write(b"DNS/0.1\t400\tMalformed\r\n")
        await writer.drain()
        writer.close()
        await writer.wait_closed()
        return

    if request_line == 'INS':
        DNS_RECORD[name] = req_addr
        packet = "DNS/0.1\t200\tOK\r\n"
    elif request_line == 'RES':
        addr = DNS_RECORD.get(name)
        if addr:
            packet = f"DNS/0.1\t200\tOK\r\n{addr}\r\n"
        else:
            packet = "DNS/0.1\t404\tNot Found\r\n"
    else:
        packet = "DNS/0.1\t400\tUnknown\r\n"

    writer.write(packet.encode('utf-8'))
    await writer.drain()
    writer.close()
    await writer.wait_closed()

async def main():
    server = await asyncio.start_server(handle_client, '127.0.0.1', 8080)
    print("DNS TCP server running on port 8080")
    async with server:
        await server.serve_forever()

asyncio.run(main())