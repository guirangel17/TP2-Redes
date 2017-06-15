# chat_server.py

import sys
import socket
import select
import struct

HOST = ''
SOCKET_LIST = []
RECV_BUFFER = 4096
PORT = 0

def getCHK(pkt):
	CHK = ""
	i = 0
	for chunk in pkt:
		if i == 8 or i == 9:
			CHK = CHK + chunk
		i = i + 1

	return CHK

def getLEN(pkt):
	LEN = ""
	i = 0
	for chunk in pkt:
		if i == 10 or i == 11:
			LEN = LEN + chunk
		i = i + 1

	return LEN

def getTYP(pkt):
	TYP = ""
	i = 0
	for chunk in pkt:
		if i == 12 or i == 13:
			TYP = TYP + chunk
		i = i + 1

	return TYP

def getID_F(pkt):
	ID_F = ""
	i = 0
	for chunk in pkt:
		if i == 14 or i == 15:
			ID_F = ID_F + chunk
		i = i + 1

	return ID_F

def getID_T(pkt):
	ID_T = ""
	i = 0
	for chunk in pkt:
		if i == 16 or i == 17:
			ID_T = ID_T + chunk
		i = i + 1

	return ID_T

def getSQN(pkt):
	SQN = ""
	i = 0
	for chunk in pkt:
		if i == 18 or i == 19:
			SQN = SQN + chunk
		i = i + 1

	return SQN

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

'''
Formato do quadro:
SYNC SYNC CHK LEN TYP ID_F ID_T SQN MSG 
4    4    2   2   2   2    2    2
'''

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

	pkt = SYNC + SYNC + CHK + LEN + TYP + ID_F + ID_T + SQN + msg
	
	if len(msg) % 2 != 0:
		chk = "%04x" % checksum(SYNC + SYNC + CHK + LEN + TYP + ID_F + ID_T + SQN + '\x00' + msg)
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

	# print 'Data sent: ' + ' '.join('%02X' % ord(x) for x in toSend)
	# print ' '.join('%02X' % ord(x) for x in getMSG(toSend))

	return toSend

def chat_server():
    if len(sys.argv) != 2:
        print 'Execution format : python server.py [PORT]'
        sys.exit()

    PORT = int(sys.argv[1])

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(10)

    # add server socket object to the list of readable connections
    SOCKET_LIST.append(server_socket)

    

    print "Chat server started on port " + str(PORT)

    while 1:

        # get the list sockets which are ready to be read through select
        # 4th arg, time_out  = 0 : poll and never block
        ready_to_read, ready_to_write, in_error = select.select(SOCKET_LIST, [], [], 0)

        for sock in ready_to_read:
            # a new connection request recieved
            if sock == server_socket:
                sockfd, addr = server_socket.accept()
		# acho que esse SOCKET_LIST vai ter que associar um ID para cada socket
                SOCKET_LIST.append(sockfd)
                print "Client (%s, %s) connected" % addr

                broadcast(server_socket, sockfd, "[%s:%s]"% addr, "entered our chatting room\n")

            # a message from a client, not a new connection
            else:
                # process data recieved from client,
                try:
                    # receiving data from the socket.
               	    data = sock.recv(RECV_BUFFER)
		    
		    if data:
			#verifica o parametro tipo das mensagens 
		        check_type(data)
		
                        # there is something in the socket
                        broadcast(server_socket, sock, "\r" + '[' + str(sock.getpeername()) + '] ', getMSG(data))
                    else:
                        # remove the socket that's broken
                        if sock in SOCKET_LIST:
                            SOCKET_LIST.remove(sock)

                        # at this stage, no data means probably the connection has been broken
                        broadcast(server_socket, sock, "Client (%s, %s)"% addr, "is offline\n")

                        # exception
                except:
                    broadcast(server_socket, sock, "Client (%s, %s)"% addr, "is offline\n")
                    continue

    server_socket.close()


def check_type (data): 
	msg_type = getTYP(data)
	
	# 1 - OK
	if msg_type == 1: 
		# do something
		print 'TYP = OK'
	
	# 2 -ERRO	
	elif msg_type == 2: 
		# do something
		print 'TYP = ERRO'

	# 3 -OI	
	elif msg_type == 3: 
		print 'TYP = OI'
		# o servidor tem que enviar um numero de identificacao ao cliente
		# se cliente == 1 (emissor):
		#	ID = entre 1 e 2^12-1 
		#	armazenar ID na lista de conectados
		# se cliente == 0 (exibidor):
		# 	ID = entre 2^12 e 2^13-1
		#	armazenar ID na lista de conectados

	# 4 -FLW	
	elif msg_type == 4: 
		print 'TYP = FLW'
		# se cliente == emissor:
		# 	se emissor tiver exibidor associado:
		#		envia FLW pro exibidor desconecta esse emissor
		#		recebe OK do exibidor
		#	senao:
		#		desconecta emissor
		#		envia mensagem OK

	# 5 -MSG	
	elif msg_type == 5: 
		print 'TYP = MSG'
		# msg comeca com um inteiro logo apos o cabecalho, indicando o numero de caracteres (C) sendo transmitidos. Depois do inteiro, seguem os bytes da mensangem em ASCII. 
		# msg = len(msg) + msg
		
		# se id_destino eh um emissor (entre 1 e 2^12-1):
		# 	identifica qual exibidor esta associado a esse emissor
		# 	envia a mensagem para o exibidor
		# 	erro: se nao existir exibidor associado ao emissor de destino
		# se id_destino eh um exibidor (entre 2^12 e 2^13-1):
		#	envia mensagem para o exibidor
		#	erro: exibidor inexistente
		# se id_destino = 0
		# 	faz broadcast para todos os exibidores conectados
		# senao 
		#	erro
		
	# 6 -CREQ	
	elif msg_type == 6: 
		print 'TYP = CREQ'	
		# CLIST = numero de clientes conectados + lista de clientes conectados
			
		# if id_destino == emissor:
		# 	identifica exibidor associado a esse emissor
		# 	envia CLIST para o exibidor associado
		# 	envia OK para emissor
		# if id_destinno == exibidor:
		# 	envia CLIST para exibidor
		# 	envia OK para emissor
		# if id_destino == 0:
		# 	envia CLIST para TODOS exibidores conectados

	# 7 -CLIST	
	elif msg_type == 7: 
		print 'TYP = CLIST'
		# o servidor eh sempre remetente do CLIST, portanto nao deveria recebe-lo 
		# acho que pode deletar esse IF

	else:
		print ''


# broadcast chat messages to all connected clients
def broadcast(server_socket, sock, ID_F, message):
    for socket in SOCKET_LIST:
        # send the message only to peer
        if socket != server_socket and socket != sock:
            try:
                socket.send(make_pkt(0,0,0,0,ID_F+message))
            except:
                # broken socket connection
                socket.close()
                # broken socket, remove it
                if socket in SOCKET_LIST:
                    SOCKET_LIST.remove(socket)


if __name__ == "__main__":
    sys.exit(chat_server())
