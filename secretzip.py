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
from curses.textpad import rectangle

files = {}
key = None
fn = None

def main():
	global files, key, fn
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
	
	nfiles = {}
	for f in files:
		nfiles["./" + f] = files[f]
	files = nfiles

	wrapper(gui)

bfiles = {}

def gui(stdscr):
	global files, bfiles
	
	stdscr.clear()
	stdscr.refresh()

	curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
	
	k = 0
	s = 0
	notif_w = 40
	notif_h = 7
	notif = curses.newwin(notif_h, notif_w, 0, 0)
	curses.curs_set(0)
	
	copy = {}
	
	while True:
		stdscr.clear()
		
		height, width = stdscr.getmaxyx()

		notif.mvwin(height // 2 - (notif_h // 2), width // 2 - (notif_w // 2))
		
		stdscr.addstr(0, 0, "SecretZIP", curses.A_BOLD)
		
		r = rec()
		
		for n, f in enumerate(r):
			stdscr.addstr(2 + n, f["i"] * 2, f["x"], (curses.A_UNDERLINE if n == s else curses.A_NORMAL))
		
		stdscr.refresh()
		
		k = stdscr.getch()
		
		if k == ord("u"):
			if bfiles != dict():
				files = bfiles.copy()
		
		bfiles = files.copy()
		
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
		elif k == 127:
			if r[s]["fn"] in files:
				draw_notif("Ya sure? y/N", notif, notif_w, notif_h)
				if stdscr.getch() == ord("y"):
					del files[r[s]["fn"]]
					r = rec()
					l = len(r)
					if s >= l:
						s = l - 1
					if s <= 0:
						s = 0
		elif k == curses.KEY_F2:
			oname = r[s]["x"]
			fname = r[s]["fn"]
			if fname != ".":
				name = take_input(stdscr, r[s]["i"] * 2, 2 + s, len(r[s]["x"]), oname)
				if (not name == oname) and name != "":
					fname_p = pathlib.Path(fname)
					if fname in files:
						files["./" + str(fname_p.parent / name)] = files[fname]
						del files[fname]
					else:
						rname = {}
						for f in files:
							if f.startswith(fname):
								fp = pathlib.Path(f)
								rname[f] = "./" + str(fname_p.parent / name / fp.relative_to(fname_p))
						for f in rname:
							files[rname[f]] = files[f]
							del files[f]
		elif k == ord("c"):
			if r[s]["fn"] in files:
				copy = {r[s]["x"]: files[r[s]["fn"]]}
			else:
				copy = {}
				for f in files:
					if f.startswith(r[s]["fn"]):
						copy[str(pathlib.Path(f).relative_to(pathlib.Path(r[s]["fn"]).parent))] = files[f]
		elif k == ord("p"):
			if not r[s]["fn"] in files:
				for c in copy:
					files["./" + str(pathlib.Path(r[s]["fn"]) / c)] = copy[c]
		elif k == ord("w"):
			d = BytesIO()
			z = ZipFile(d, mode="w")
			for f in files:
				z.writestr(f[2:], files[f])
			z.close()
			
			d.seek(0)
			d = d.read()
			
			d = encrypt(key, d)
			
			f = open(fn, "wb")
			f.write(d)
			f.close()
			draw_notif("Wrote to file.", notif, notif_w, notif_h)
			stdscr.getch()

def draw_notif(m, f, fw, fh):
	if len(m) >= fw - 3:
		return
	f.addstr(fh // 2, 1 + (fw // 2) - (len(m) // 2) - 1, m)
	rectangle(f, 0, 0, fh - 1, fw - 2)
	f.refresh()

def take_input(stdscr, x, y, lclear, start_text):
	curses.curs_set(1)
	escdelay = curses.get_escdelay()
	curses.set_escdelay(25)
	stdscr.move(y, x)
	for i in range(lclear):
		stdscr.delch(y, x)
	
	k2 = None
	text = start_text
	
	stdscr.addstr(text)
	stdscr.refresh()
	while (k2 := stdscr.getch()) != ord("\n"):
		if k2 == 127:
			if len(text) > 0:
				text = text[:-1]
				stdscr.delch(stdscr.getyx()[0], stdscr.getyx()[1] - 1)
		elif k2 == 27:
			text = start_text
			break
		else:
			text += chr(k2)
			try:
				stdscr.echochar(chr(k2))
			except OverflowError: #Really lazy solution, but it works well enough
				text = text[:-1]
	curses.curs_set(0)
	curses.noecho()
	curses.set_escdelay(escdelay)
	return text

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
