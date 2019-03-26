HTTP2WebSocket
===============
**Latest release**: 1.0<br>
**License**: GNU GPL

HTTP2WebSocket is tool to translate HTTP/1.1 traffic into Web Sockets traffic.
It can be used in conjunction with standard pentesting tools like sqlmap, dirb, commix or others.<br>
It supports:
* SSL (wss://)
* Proxy
* WS connection initiation based on HTTP Host header

## Requirements
* request
* websocket-client

```bash
pip3 install request websocket-client
```

## Installation
No installation is required.

## Usage
HTTP2WebSocket act as a proxy between HTTP and Web Socket connection. It expects HTTP incomming traffic and translates it to Web Socket application.<br>
GET method is used to discover endpoinds.<br>
POST method is used to sent data to a web socket application.<br>
HTTP2WebSocket can work in two ways. The default one is passing the exact HTTP body to the web socket. The second one is passing only the value of the parameter provided.<br>
HTTP2WebSocket can be binded to a specific application (-t parameter) or it can be provided in each HTTP request through Host header.

## Examples
Examples are based on Damn Vulnerable Web Socket virtual machine.<br>
Details on how to setup DVWS here: [DVWS](https://github.com/interference-security/DVWS)<br>
Docker image of DVWS: [DVWS docker image](https://github.com/tssoffsec/docker-dvwsocket)

### One WS app - full POST body
Run the listener on port 3333 and connect to dvws.local:8080 web socket app on every HTTP request:
```bash
python3 HTTP2WebSocket.py -l 3333 -t ws://dvws.local:8080
```

Brute force:
```bash
for i in 'abc' 'qwe' 'admin' 'asd' 'zxc'; do echo -n $i|base64; done > dict-passwords.b64
hydra -t 1 -L dict-passwords.b64 -P dict-passwords.b64 -s 3333 127.0.0.1 http-form-post /authenticate-user-prepared:'{"auth_user"\:"^USER^","auth_pass"\:"^PASS^"}':Incorrect
```

Command execution:
```bash
curl "http://127.0.0.1:3333/command-execution" -d '|id'
```

File inclusion:
```bash
curl --data '/etc/passwd' 127.0.0.1:3333/file-inclusion
```

Error SQL injection:
```bash
sqlmap -u http://127.0.0.1:3333/authenticate-user --data '{"auth_user":"YWFhYWE=","auth_pass":"YWFh"}' --tamper=base64encode --banner
```

Blind SQL injection:
```bash
sqlmap -u http://127.0.0.1:3333/authenticate-user-blind --data '{"auth_user":"YWFhYWE=","auth_pass":"YWFh"}' --tamper=base64encode --banner
```

Reflected XSS:
```bash
python2 xsssniper.py -u http://127.0.0.1:3333/reflected-xss --post --data="whatever"
```

Stored XSS:
```bash
curl http://127.0.0.1:3333/post-comments --data '{"name":"zzz","comment":"<script>alert(1111)</script>"}'
curl http://127.0.0.1:3333/show-comments -X POST
```

Discovering endpoints:
```bash
dirb http://127.0.0.1:3333/ endpoints-wordlist.txt
```

Other stuff:
```bash
nikto -host http://127.0.0.1:3333/
```

### One WS app - POST body parameter value
Run the listener on port 4444 and connect to dvws.local:8080 web socket app on every HTTP request.<br>
It sends value of the HTTP POST body parameter *fuzz*. Some tools (E.g. commix) don't recognise plain body which is used by WS app.<br>
```bash
python3 HTTP2WebSocket.py -l 4444 -t ws://dvws.local:8080 -P fuzz
```

Command execution:
```bash
python2 commix.py --url "http://127.0.0.1:4444/command-execution" --data "fuzz=127.0.0.1" --skip-empty --technique=C --hostname
```

File inclusion :
```bash
python2 fimap.py -s -b --no-auto-detect -u "http://127.0.0.1:4444/file-inclusion" -P "fuzz=xxx"
```

### Multiple WS apps - full POST body
Run the listener on port 5555. Take Host header from each HTTP request and use it as a target WS application.<br>
*NOTE: Protocol type has to be provided in HTTP Host header (E.g. Host: wss://localhost:1234)*

```bash
python3 HTTP2WebSocket.py -l 5555
```

Brute force:
```bash
hydra -t 1 -L dict-passwords.b64 -P dict-passwords.b64 -s 5555 127.0.0.1 http-form-post /authenticate-user-prepared:'{"auth_user"\:"^USER^","auth_pass"\:"^PASS^"}':Incorrect:"H=Host: ws\://dvws.local\:8080"
```

Command execution:
```bash
curl "http://127.0.0.1:5555/command-execution" -d '|id' -H 'Host: ws://dvws.local:8080'
```

Discover endpoints:
```bash
dirb http://127.0.0.1:5555/ ~/endpoints-wordlist.txt -H Host:ws://dvws.local:8080
```

Other:
```bash
nikto -host http://127.0.0.1:5555/ -vhost ws://dvws.local:8080
```

### Multiple WS apps - POST body parameter value
Run the listener on port 6666. Take Host header from HTTP request and use it as a target WS application.<br>
In this example actual data which is passed to the web socket application is the value of the *fuzz* parameter.
```bash
python3 HTTP2WebSocket.py -l 6666 -P fuzz
```

Command execution:
```bash
python2 commix.py --url "http://127.0.0.1:6666/command-execution" --data "fuzz=127.0.0.1" --skip-empty --technique=C --hostname --host="ws://dvws.local:8080"
```

File inclusion:
```bash
curl --data '/etc/passwd' 127.0.0.1:6666/file-inclusion -H 'Host: ws://dvws.local:8080'
```

Error SQL injection:
```bash
sqlmap -u http://127.0.0.1:6666/authenticate-user --data '{"auth_user":"YWFhYWE=","auth_pass":"YWFh"}' --tamper=base64encode --banner --host="ws://dvws.local:8080"
```

Blind SQL injection:
```bash
sqlmap -u http://127.0.0.1:6666/authenticate-user-blind --data '{"auth_user":"YWFhYWE=","auth_pass":"YWFh"}' --tamper=base64encode --banner --host=ws://dvws.local:8080
```

### All options example
Single example of all the options of HTTP2WebSocket:<br>

In this example actual data which is passed to the web socket application is the value of the *fuzz* parameter.
```bash
python HTTP2WebSocket.py -l 7777 -t wss://dvws.local:8765 -P fuzz -v -k -p 127.0.0.1:8080
```

|Parameter|Description|
|---|---|
|*-l 7777*|Listen on port 7777/TCP|
|*-t wss://dvws.local:8765*|Bind to dvws.local:8765 WS application through SSL|
|*-P fuzz*|Extract the value of the POST body parameter named *fuzz* and pass it to WS application|
|*-v*|Verbose mode|
|*-k*|Ignore SSL warnings and errors|
|*-p 127.0.0.1:8080*|Send all traffic through jttp proxy: 127.0.0.1:8080|

Sending simple request:
```bash
curl http://127.0.0.1:7777/authenticate-user -v -d 'fuzz=dawid'
```