# chat_client.py

import sys
import socket
import select
import struct

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


def chat_client():
    if (len(sys.argv) < 3):
        print 'Usage : python chat_client.py hostname port'
        sys.exit()

    host = sys.argv[1]
    port = int(sys.argv[2])

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)

    # connect to remote host
    try:
        s.connect((host, port))
    except:
        print 'Unable to connect'
        sys.exit()

    print 'Connected to remote host. You can start sending messages'
    sys.stdout.write('>> ')
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
                    print '\nDisconnected from chat server'
                    sys.exit()
            else:
                # user entered a message
                sys.stdout.write('>> ')
                sys.stdout.flush()
                msg = sys.stdin.readline()
		typ = check_TYP(msg.strip())
		s.send(make_pkt(typ,0,0,0,msg))

def check_TYP(msg):
	if msg == 'OI':
		return 3;
	elif msg == 'FLW':
		return 4;
	elif msg == 'CREQ': 
		return 6;
	else: 
		return 5;	
	


if __name__ == "__main__":
    sys.exit(chat_client())
