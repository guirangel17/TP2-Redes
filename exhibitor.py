# chat_client.py

import sys
import socket
import select
import struct

'''
Formato do quadro:
SYNC SYNC CHK TYP ID_F ID_T SQN LEN MSG 
4    4	  2   2   2    2	  2	  2
'''

def getCHK(pkt):
	CHK = ""
	i = 0
	for chunk in pkt:
		if i == 8 or i == 9:
			CHK = CHK + chunk
		i = i + 1

	return CHK

def getTYP(pkt):
	TYP = ""
	i = 0
	for chunk in pkt:
		if i == 10 or i == 11:
			TYP = TYP + chunk
		i = i + 1

	return int(toString(TYP),16)

def getID_F(pkt):
	ID_F = ""
	i = 0
	for chunk in pkt:
		if i == 12 or i == 13:
			ID_F = ID_F + chunk
		i = i + 1

	return int(toString(ID_F),16)

def getID_T(pkt):
	ID_T = ""
	i = 0
	for chunk in pkt:
		if i == 14 or i == 15:
			ID_T = ID_T + chunk
		i = i + 1

	return int(toString(ID_T),16)

def getSQN(pkt):
	SQN = ""
	i = 0
	for chunk in pkt:
		if i == 16 or i == 17:
			SQN = SQN + chunk
		i = i + 1

	return int(toString(SQN),16)

def getLEN(pkt):
	LEN = ""
	i = 0
	for chunk in pkt:
		if i == 18 or i == 19:
			LEN = LEN + chunk
		i = i + 1

	return int(toString(LEN),16)

def getMSG(pkt):
	MSG = ""
	i = 0
	for chunk in pkt:
		if i > 19:
			MSG = MSG + chunk
		i = i + 1

	return MSG

def carry_around_add(a, b):
	c = a + b
	return(c &0xffff)+(c >>16)

def checksum(msg):
	s =0
	for i in range(0, len(msg),2):
		w = ord(msg[i])+(ord(msg[i+1])<<8)
		s = carry_around_add(s, w)
	return~s &0xffff

def toBytes(var):
	toStr = format(var, '04x')
	return struct.pack('B',int(toStr[0]+toStr[1],16)) + struct.pack('B',int(toStr[2]+toStr[3],16))

def toString(data):
	return ''.join('%02X' % ord(x) for x in data)

def make_pkt(typeMsg, idFrom, idTo, sqNumber, msg):
	SYNC = '\xDC\xC0\x23\xC2'
	CHK = '\x00\x00'
	LEN = toBytes(len(msg))
	TYP = toBytes(typeMsg)
	ID_F = toBytes(idFrom)
	ID_T = toBytes(idTo)
	SQN = toBytes(sqNumber)
	
	msg = map(lambda x: ord(x), msg)
	msg = struct.pack("%dB" % len(msg), *msg)

	pkt = SYNC + SYNC + CHK + TYP + ID_F + ID_T + SQN + LEN + msg
	
	if len(msg) % 2 != 0:
		chk = "%04x" % checksum(SYNC + SYNC + CHK + TYP + ID_F + ID_T + SQN + '\x00' + LEN + msg)
	else:
		chk = "%04x" % checksum(pkt)

	chkSecondByte = struct.pack('B',int(chk[0]+chk[1],16))
	chkFirstByte = struct.pack('B',int(chk[2]+chk[3],16))

	toSend = ''
	i = 0
	for chunk in pkt:
		if i == 8 or i == 9:
			if i == 8:
				toSend = toSend + chkFirstByte
			else:
				toSend = toSend + chkSecondByte
		else:
			toSend = toSend + chunk
		i = i + 1

	return toSend

def chat_exhibitor():
	if len(sys.argv) != 2:
		print 'Execution format: $ python exhibitor.py [IP_ADDRESS]:[PORT]'
		sys.exit()
   
	host = sys.argv[1].split(":")[0]
	port = int (sys.argv[1].split(":")[1])

	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.settimeout(2)

	# connect to remote host
	try:
		s.connect((host, port))
	except:
		print 'Unable to connect. Check if you tried a valid port.'
		sys.exit()

	SQN = 0

	# Assim que conecta no servidor, o exibidor tem que enviar uma mensagem OI para saber qual seu numero de identificacao	
	# O servidor tem id = 2^16-1 = 65535
	# Envia 0 no id_from pois eh um exibidor
	SQN = SQN + 1
	s.send(make_pkt(3,0,65535,SQN,"Novo exibidor"))

	handshake = s.recv(1024)
	typMsg = getTYP(handshake)
	myID = getID_T(handshake)

	if typMsg == 2:
		print 'Error. Sequence number: ' + str(getSQN(handshake)) + ". Message: " + getMSG(handshake)
	
	if typMsg == 1:
		print 'Exhibitor connected to remote host as client ID #' + str(myID) 

		sys.stdout.flush()

		while 1:
			socket_list = [sys.stdin, s]

			# Get the list sockets which are readable
			ready_to_read, ready_to_write, in_error = select.select(socket_list, [], [])

			for sock in ready_to_read:
				if sock == s:
					# incoming message from remote server, s
					data = sock.recv(4096)
		
					if not data:
						continue
					else:
						if getTYP(data) == 5:
							sys.stdout.write("Mensagem recebida de cliente ID # " + str(getID_F(data)) + ": " + getMSG(data))
							sys.stdout.flush()

						elif getTYP(data) == 4:
							sys.stdout.write("Cliente ID # " + str(getID_F(data)) + " finalizou sua conexao. Encerrando este exibidor associado")
							sys.stdout.flush()
							SQN = SQN + 1
							sock.send(make_pkt(1, int(myID), 65535, getSQN(data), "Conexao encerrada"))
							sys.exit()
						elif getTYP(data) == 7:
							sys.stdout.write(getMSG(data))
							sys.stdout.flush()

				else:
					sys.stdout.flush()

if __name__ == "__main__":
	sys.exit(chat_exhibitor())
