# chat_server.py

import sys
import socket
import select
import struct

HOST = ''
SOCKET_LIST = []
RECV_BUFFER = 4096
PORT = 0

ID_sender = 0
ID_exhibitor = 4095

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

def chat_server():
	if len(sys.argv) != 2:
		print 'Execution format: $ python server.py [PORT]'
		sys.exit()

	PORT = int(sys.argv[1])

	server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	server_socket.bind((HOST, PORT))
	server_socket.listen(10)

	# Add server socket object to the list of readable connections
	SOCKET_LIST.append(server_socket)
	

	print "Chat server started on port " + str(PORT)

	emissorSockets = {} # IDs from 1 to 2047
	exibidorSockets = {} # IDs from 2048 to 4096
	oldIDs = [] # IDs que ja foram encerradas

	exibidorAssociado = {} # Dicionario onde cada item representa um emissor e o valor correspondente o exibidor associado
	emissorAssociado = {} # Contrario do dicionario acima

	SQN = 0

	while 1:

		# Get the list sockets which are ready to be read through select
		# 4th arg, time_out  = 0 : poll and never block
		ready_to_read, ready_to_write, in_error = select.select(SOCKET_LIST, [], [], 0)

		for sock in ready_to_read:
			# A new connection request recieved
			if sock == server_socket:
				sockfd, addr = server_socket.accept()
				SOCKET_LIST.append(sockfd)
				

			# A message from a client, not a new connection
			else:
				try:
					# Receiving data from the socket
					data = sock.recv(RECV_BUFFER)

					if data:

						# ID = 3 (OI) 
						if getTYP(data) == 3:
							# Conexao recebida de um exibidor
							if getID_F(data) == 0:
								exibidorSockets[len(exibidorSockets)+4096] = sock
								print "Exibidor ID # " + str(len(exibidorSockets)+4095) + " conectado"
								SQN = SQN + 1
								sock.send(make_pkt(1,65535,len(exibidorSockets)+4095,getSQN(data),""))

							# Conexao recebida de um emissor
							else:
								if getID_F(data) >= 4096 and getID_F(data) <= 8191:
									if getID_F(data) in exibidorSockets and getID_F(data) not in oldIDs:
										emissorSockets[len(emissorSockets)+1] = sock
										print "Emissor ID # " + str(len(emissorSockets)) + " conectado e associado com o Exibidor ID # " + str(getID_F(data))

										exibidorAssociado[len(emissorSockets)] = getID_F(data)
										emissorAssociado[getID_F(data)] = len(emissorSockets)
										SQN = SQN + 1
										sock.send(make_pkt(1,65535,len(emissorSockets),getSQN(data),""))

									else:
										# Caso um novo emissor esteja tentando se associar a um exibidor nao existente, erro, retornando o mesmo id que desejava se associar
										SQN = SQN + 1
										sock.send(make_pkt(2,65535,getID_F(data),getSQN(data),"Exibidor nao existente"))

								else:
									emissorSockets[len(emissorSockets)+1] = sock
									print "Emissor ID # " + str(len(emissorSockets)) + " conectado"
									SQN = SQN + 1
									sock.send(make_pkt(1,65535,len(emissorSockets),getSQN(data),""))

						# ID = 4 (FLW)
						if getTYP(data) == 4:
							# mandar um OK de volta e terminar a conexao com o cliente
							SQN = SQN + 1
							sock.send(make_pkt(1, 65535, getID_F(data), getSQN(data), "Conexao encerrada"))
							# verificar se tem exibidor asociado ao cliente, se houver manda um flw, ai o exibidor termina sua execucao

							if getID_F(data) in exibidorAssociado:
								SQN = SQN + 1
								exibidorSockets[exibidorAssociado[getID_F(data)]].send(make_pkt(4, getID_F(data), getID_T(data), getSQN(data), getMSG(data)))
								oldIDs.append(exibidorAssociado[getID_F(data)])
								SOCKET_LIST.remove(exibidorSockets[exibidorAssociado[getID_F(data)]])

							if sock in SOCKET_LIST:
								oldIDs.append(getID_F(data))
								SOCKET_LIST.remove(sock)
							sock.close()


						# ID = 5 (MSG)
						if getTYP(data) == 5:
							if getID_T(data) == 0:
								SQN = SQN + 1
								broadcast(server_socket, sock, data, getMSG(data))
							else:
								if getID_T(data) in exibidorAssociado:
									if exibidorAssociado[getID_T(data)] in exibidorSockets:
										SQN = SQN + 1
										exibidorSockets[exibidorAssociado[getID_T(data)]].send(make_pkt(getTYP(data), getID_F(data), getID_T(data), getSQN(data), getMSG(data)))

								else:
									if getID_T(data) >= 4096 and getID_T(data) <= 8191:
										SQN = SQN + 1
										exibidorSockets[getID_T(data)].send(make_pkt(getTYP(data), getID_F(data), getID_T(data), getSQN(data), getMSG(data)))
									else:
										# o emissor nao possui exibidor associado
										SQN = SQN + 1
										sock.send(make_pkt(2,65535,getID_F(data),getSQN(data),"Exibidor nao associado"))


						# ID = 6 (CREQ)
						if getTYP(data) == 6:
							# Mandando ok para o emissor
							SQN = SQN + 1
							sock.send(make_pkt(1, 65535, getID_F(data), getSQN(data), ""))

							# Achando o cliente pra mandar a lista
							if getID_T(data) in exibidorAssociado:
								if exibidorAssociado[getID_T(data)] in exibidorSockets:
									numberOfConnectedClients = len(exibidorSockets) + len(emissorSockets)
									listOfExhibitors = '\n'.join(str(e) for e in exibidorSockets)
									listOfEmissor = '\n'.join(str(e) for e in emissorSockets)

									message = "\nNumero de clientes conectados: " + str(numberOfConnectedClients) + "\nLista de clientes: \n" + listOfExhibitors + "\n" + listOfEmissor
									SQN = SQN + 1
									exibidorSockets[exibidorAssociado[getID_T(data)]].send(
										make_pkt(7, 65535, getID_T(data), getSQN(data), message))
							else:
								if getID_T(data) >= 4096 and getID_T(data) <= 8191:
									numberOfConnectedClients = len(exibidorSockets) + len(emissorSockets) - len(oldIDs)
									listOfExhibitors = '\n'.join(str(e) for e in exibidorSockets if e not in oldIDs)
									listOfEmissor = '\n'.join(str(e) for e in emissorSockets if e not in oldIDs)

									message = "\nNumero de clientes conectados: " + str(
										numberOfConnectedClients) + "\nLista de clientes: \n" + listOfExhibitors + "\n" + listOfEmissor
									SQN = SQN + 1
									exibidorSockets[getID_T(data)].send(
										make_pkt(7, 65535, getID_T(data), getSQN(data), message))
								else:
									# o emissor nao possui exibidor associado
									SQN = SQN + 1
									sock.send(make_pkt(2, 65535, getID_F(data), getSQN(data), "Exibidor nao associado"))

					else:
						# remove the socket that's broken
						if sock in SOCKET_LIST:
							SOCKET_LIST.remove(sock)

				# exception
				except:
					SQN = SQN + 1
					broadcast(server_socket, sock, data, "Client is offline\n")
					continue

	server_socket.close()


# broadcast chat messages to all connected clients
def broadcast(server_socket, sock, data, message):
	for socket in SOCKET_LIST:
		# send the message only to peer
		if socket != server_socket and socket != sock:
			try:
				socket.send(make_pkt(getTYP(data), getID_F(data), getID_T(data), getSQN(data), message))
			except:
				# broken socket connection
				socket.close()
				# broken socket, remove it
				if socket in SOCKET_LIST:
					SOCKET_LIST.remove(socket)


if __name__ == "__main__":
	sys.exit(chat_server())
