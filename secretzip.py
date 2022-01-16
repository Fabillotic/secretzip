from Crypto.Cipher import AES
from Crypto.Hash import SHA3_256
from Crypto.Random import get_random_bytes as rand
import pathlib
from pwinput import pwinput as getpass
from sys import argv as args
import argparse
from zipfile import ZipFile
from zipfile import Path as ZPath
from io import BytesIO

import curses
from curses import wrapper

files = {}

def main():
	global files
	parser = argparse.ArgumentParser(description="Encrypt files with AES-GCM.")
	parser.add_argument("file", type=pathlib.Path)
	parser.add_argument("-n", "--new", dest="new", action="store_true", help="Create a new archive.")
	
	args = vars(parser.parse_args())
	fn = args.get("file").absolute()
	nmode = args.get("new")
	
	pwd = getpass().encode("utf-8")
	key = SHA3_256.new(pwd).digest()

	if nmode:
		d = BytesIO()
		z = ZipFile(d, mode="w")
		z.writestr("one/two/test.txt", b"Hello, world!")
		z.writestr("three/test.txt", b"Hello, world!")
		z.writestr("one/two/another/lol.txt", b"Hello, world!")
		z.writestr("one/two/another/lol2.txt", b"Hello, world!")
		z.close()
		
		d.seek(0)
		d = d.read()

		d = encrypt(key, d)
		
		f = open(fn, "wb")
		f.write(d)
		f.close()
		return
	
	f = open(fn, "rb")
	d = f.read()
	f.close()
	
	d = decrypt(key, d)
	
	if not d:
		print("Invalid password!")
		return
	
	d = BytesIO(d)
	
	z = ZipFile(d, mode="r")
	for n in z.namelist():
		files[n] = z.read(n)
	z.close()

	wrapper(gui)

def gui(stdscr):
	global files
	
	stdscr.clear()
	stdscr.refresh()

	curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
	
	k = 0
	s = 0
	while True:
		stdscr.clear()
		curses.curs_set(0)
		
		height, width = stdscr.getmaxyx()
		
		stdscr.addstr(0, 0, "SecretZIP", curses.A_BOLD)
		
		r = rec()
		
		for n, f in enumerate(r):
			stdscr.addstr(2 + n, f["i"] * 2, f["x"], curses.color_pair(1) | (curses.A_UNDERLINE if n == s else curses.A_NORMAL))
		
		k = stdscr.getch()
		if k == 27 or k == ord("q"):
			break
		elif k == curses.KEY_DOWN:
			s += 1
			if s >= len(r):
				s = len(r) - 1
		elif k == curses.KEY_UP:
			s -= 1
			if s <= 0:
				s = 0
		
		stdscr.refresh()

def rec():
	r = {}
	def gRec(dic, fs):
		if len(fs) == 1:
			return dic[fs[0]]
		return gRec(dic[fs[0]], fs[1:])
	
	for f in files:
		fs = f.split("/")
		t = []
		for x in fs:
			if len(t) == 0:
				if not x in r:
					r[x] = {}
				t.append(x)
				continue
			if not x in gRec(r, t):
				gRec(r, t)[x] = {}
			t.append(x)
	
	l = []
	def it(d, i, fn):
		for x in sorted(d):
			y = (fn + "/" + x)
			l.append({"i": i, "x": x, "fn": y[1:]}) #indent, number, name, full name
			it(d[x], i+1, y)
	it(r, 0, "")
	return l

def encrypt(key, d):
	d_out = b""
	nonce = rand(12)
	
	d_out += nonce
	
	cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
	ct, tag = cipher.encrypt_and_digest(d)
	
	d_out += tag
	d_out += ct
	return d_out

def decrypt(key, d):
	nonce = d[:12]
	tag = d[12:28]
	ct = d[28:]
	
	cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
	try:
		pt = cipher.decrypt_and_verify(ct, tag)
	except ValueError:
		return None
	
	return pt

if __name__ == "__main__":
	main()
