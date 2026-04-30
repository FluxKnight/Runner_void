VOID RUNNER SERVER SETUP

This is a simple local/LAN server so accounts and ranks can be shared.

ON THE SERVER COMPUTER:
1. Open PowerShell in the project folder.
2. Run:
   python server/void_server.py

The server starts at:
http://127.0.0.1:5050

SAME COMPUTER GAME:
No change needed. The game uses:
data/server_config.json
{"server_url": "http://127.0.0.1:5050"}

OTHER COMPUTER ON SAME WIFI/LAN:
1. On server computer, find IP:
   ipconfig

2. Example IP:
   192.168.1.20

3. On the other game computer, edit:
   data/server_config.json

4. Put:
   {"server_url": "http://192.168.1.20:5050"}

5. Start the game.

If Windows Firewall asks, allow Python.

IMPORTANT:
- This is a simple development server.
- It is good for testing with friends on same Wi-Fi/LAN.
- It is not a secure public internet server.
