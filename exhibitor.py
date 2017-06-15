# chat_client.py

import sys
import socket
import select
import struct

'''
Formato do quadro:
SYNC SYNC CHK LEN TYP ID_F ID_T SQN MSG 
4    4    2   2   2   2    2    2
'''
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
		chk = "%04x" % checksum(SYNC + SYNC + CHK + LEN + TYP + ID_F + ID_T + SQN + '\x00' + '\x00' + msg)
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

def chat_exhibitor():
    if len(sys.argv) != 2:
        print 'Exectuion format : python exhibitor.py [IP_ADDRESS]:[PORT]'
        sys.exit()
   
    host = sys.argv[1].split(":")[0]
    port = int (sys.argv[1].split(":")[1])

    print host 
    print port

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)

    # connect to remote host
    try:
        s.connect((host, port))
    except:
        print 'Unable to connect'
        sys.exit()

    # Assim que conecta no servidor, o exibidor tem que enviar uma mensagem OI para saber qual seu numero de identificacao	
    # O servidor tem id = 2^16-1 = 65535
    # Envia 0 no id_from pois eh um exibidor
    # s.send(make_pkt(3,0,65535,0,"Novo exibidor"))


    print 'Exhibitor connected to remote host.'
    sys.stdout.flush()

    while 1:
        socket_list = [sys.stdin, s]

        # Get the list sockets which are readable
        ready_to_read, ready_to_write, in_error = select.select(socket_list, [], [])

        for sock in ready_to_read:
            if sock == s:
                # incoming message from remote server, s
                data = sock.recv(4096)
		
		if data:
		    check_type(data)
		
                if not data:
                    print '\nDisconnected from chat server'
                    sys.exit()
                else:
                    sys.stdout.write(getMSG(data))
                    sys.stdout.flush()

            else:
                sys.stdout.flush()

def check_type(data):
	msg_type = getTYP(data)
	
	# 1 - OK
	if msg_type == '1':
		print 'TYP = OK'
		# se for o primeiro OK, deve conter o identificador desse exibidor
		# pega o numero de identificacao que veio no pacote -> getID_F()
		# armazena o ID desse exibidor para ser usado por todas suas operacoes
		# exibe o ID na tela
		
		# se o exibidor ja possuir numero de identificacao, nao faz nada, o OK eh so pra falar que a mnsg chegou ao destinatario
	
	# 2 - ERRO
	elif msg_type  == '2':
		print 'TYP = ERRO'
		# informa o numero de sequencia e conteudo da mensagem que nao foi enviada corretamente

	# 3 -OI	
	elif msg_type == 3: 
		print 'TYP = OI'
		# o exibidor nao recebe OI, pode ser excluido

	# 4 -FLW	
	elif msg_type == 4: 
		print 'TYP = FLW'
		# if id_from == 65555 (servidor):
		# 	envia mensagem OK para o servidor
		# 	termina conexao do exibidor
		# if id_from == emissor: 
		# 	envia mensagem OK para o servidor
		# 	termina conexao do emissor 
		# 	exibe mensagem na tela


	# 5 - MSG	
	elif msg_type == 5:
		print 'TYP = MSG'
		# exibe id_from 
		# enquanto (len(msg)):
		# 	monta mensagem 
		# exibe mensagem
		
	# 6 -CREQ	
	elif msg_type == 6: 
		print 'TYP = CREQ'	
		# nao envolve o exibidor, pode ser deletado


	# 7 -CLIST	
	elif msg_type == 7: 
		print 'TYP = CLIST'
		# exibe id_from
		# enquanto (len(CLIST)):
		# 	monta CLIST
		# exibe CLIST
		# envia OK para servidor
	
	else:
		print ''



if __name__ == "__main__":
    sys.exit(chat_exhibitor())
