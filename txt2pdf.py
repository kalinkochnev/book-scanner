#!/usr/bin/env python
 
"""
 pyText2Pdf - Python script to convert plain text files into Adobe
 Acrobat PDF files with support for arbitrary page breaks etc.
 
 Version 2.0
 
 Author: Anand B Pillai <abpillai at gmail dot com>
 Derived from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/189858
"""
 
import optparse
import os
import re
import string
import sys
import time
import io
 
LF_EXTRA = 0
LINE_END = '\015'
# form feed character (^L)
FF = chr(12)
 
ENCODING_STR = """\
/Encoding <<
/Differences [ 0 /.notdef /.notdef /.notdef /.notdef
/.notdef /.notdef /.notdef /.notdef /.notdef /.notdef
/.notdef /.notdef /.notdef /.notdef /.notdef /.notdef
/.notdef /.notdef /.notdef /.notdef /.notdef /.notdef
/.notdef /.notdef /.notdef /.notdef /.notdef /.notdef
/.notdef /.notdef /.notdef /.notdef /space /exclam
/quotedbl /numbersign /dollar /percent /ampersand
/quoteright /parenleft /parenright /asterisk /plus /comma
/hyphen /period /slash /zero /one /two /three /four /five
/six /seven /eight /nine /colon /semicolon /less /equal
/greater /question /at /A /B /C /D /E /F /G /H /I /J /K /L
/M /N /O /P /Q /R /S /T /U /V /W /X /Y /Z /bracketleft
/backslash /bracketright /asciicircum /underscore
/quoteleft /a /b /c /d /e /f /g /h /i /j /k /l /m /n /o /p
/q /r /s /t /u /v /w /x /y /z /braceleft /bar /braceright
/asciitilde /.notdef /.notdef /.notdef /.notdef /.notdef
/.notdef /.notdef /.notdef /.notdef /.notdef /.notdef
/.notdef /.notdef /.notdef /.notdef /.notdef /.notdef
/dotlessi /grave /acute /circumflex /tilde /macron /breve
/dotaccent /dieresis /.notdef /ring /cedilla /.notdef
/hungarumlaut /ogonek /caron /space /exclamdown /cent
/sterling /currency /yen /brokenbar /section /dieresis
/copyright /ordfeminine /guillemotleft /logicalnot /hyphen
/registered /macron /degree /plusminus /twosuperior
/threesuperior /acute /mu /paragraph /periodcentered
/cedilla /onesuperior /ordmasculine /guillemotright
/onequarter /onehalf /threequarters /questiondown /Agrave
/Aacute /Acircumflex /Atilde /Adieresis /Aring /AE
/Ccedilla /Egrave /Eacute /Ecircumflex /Edieresis /Igrave
/Iacute /Icircumflex /Idieresis /Eth /Ntilde /Ograve
/Oacute /Ocircumflex /Otilde /Odieresis /multiply /Oslash
/Ugrave /Uacute /Ucircumflex /Udieresis /Yacute /Thorn
/germandbls /agrave /aacute /acircumflex /atilde /adieresis
/aring /ae /ccedilla /egrave /eacute /ecircumflex
/edieresis /igrave /iacute /icircumflex /idieresis /eth
/ntilde /ograve /oacute /ocircumflex /otilde /odieresis
/divide /oslash /ugrave /uacute /ucircumflex /udieresis
/yacute /thorn /ydieresis ]
>>
"""
 
INTRO = """prog [options] filename
 
PyText2Pdf  makes a 7-bit clean PDF file from any input file.
 
It reads from a named file, and writes the PDF file to a file specified by
the user, otherwise to a file with '.pdf' appended to the input file.
 
Author: Anand B Pillai."""
 
 
class PyText2Pdf(object):
    """ Text2pdf converter in pure Python """
 
    def __init__(self, _ifile, _ofile):
        # version number
        self._version = "1.3"
        # iso encoding flag
        self._IsoEnc = False
        # formfeeds flag
        self._doFFs = False
        self._progname = "PyText2Pdf"
        self._appname = " ".join((self._progname, str(self._version)))
        # default font
        self._font = "/Courier"
        # default font size
        self._ptSize = 10
        # default vert space
        self._vertSpace = 12
        self._lines = 0
        # number of characters in a row
        self._cols = 80
        self._columns = 1
        # page ht
        self._pageHt = 792
        # page wd
        self._pageWd = 612


        # input file
        self._ifile = _ifile
        # output file
        self._ofile = _ofile


        # default tab width
        self._tab = 4
        # input file descriptor
        self._ifs = None
        # output file descriptor
        self._ofs = None
        # landscape flag
        self._landscape = False
        # Subject
        self._subject = ''
        # Author
        self._author = ''
        # Keywords
        self._keywords = []
        # Custom regexp  for page breaks
        self._pagebreakre = None
 
        # marker objects
        self._curobj = 5
        self._pageObs = [0]
        self._locations = [0, 0, 0, 0, 0, 0]
        self._pageNo = 0
 
        # file position marker
        self._fpos = 0
 
 
    def writestr(self, nstr):
        """ Write string to output file descriptor.
        All output operations go through this function.
        We keep the current file position also here"""
        # update current file position
        bstr = str.encode(nstr)
        self._fpos += len(bstr)
        for x in range(0, len(bstr)):
            if bstr[x] == '\n':
                self._fpos += LF_EXTRA
        try:
            self._ofs.write(bstr)
        except IOError as e:
            print (e)
            return -1
 
        return 0
 
    def convert(self):
        """ Perform the actual conversion """
 
        if self._landscape:
            # swap page width & height
            tmp = self._pageHt
            self._pageHt = self._pageWd
            self._pageWd = tmp
 
        if self._lines == 0:
            self._lines = (self._pageHt - 72) / self._vertSpace
        if self._lines < 1:
            self._lines = 1
 
        try:
            self._ifs = io.open(self._ifile)
        except IOError (strerror, errno):
            print ('Error: Could not open file to read --->', self._ifile)
            sys.exit(3)
 
        if self._ofile == "":
            self._ofile = os.path.splitext(self._ifile)[0] + '.pdf'
 
        try:
            self._ofs = open(self._ofile, 'wb')
        except IOError (strerror, errno):
            print ('Error: Could not open file to write --->', self._ofile)
            sys.exit(3)
 
        print ('Input file=>', self._ifile)
        print ('Writing pdf file', self._ofile, '...')
        self.writeheader()
        self.writepages()
        self.writerest()
 
        print ('Wrote file', self._ofile)
        self._ifs.close()
        self._ofs.close()
        return 0
 
    def writeheader(self):
        """Write the PDF header"""
 
        title = self._ifile
 
        t = time.localtime()
        timestr = str(time.strftime("D:%Y%m%d%H%M%S", t))
        self.writestr("PDF-1.4\n")
        self._locations[1] = self._fpos
        self.writestr("1 0 obj\n")
        self.writestr("<<\n")
 
        buf = "".join(("/Creator (", self._appname, " By Anand B Pillai )\n"))
        self.writestr(buf)
        buf = "".join(("/CreationDate (", timestr, ")\n"))
        self.writestr(buf)
        buf = "".join(
            ("/Producer (", self._appname, "(\\251 Anand B Pillai))\n"))
        self.writestr(buf)
        if self._subject:
            title = self._subject
            buf = "".join(("/Subject (", self._subject, ")\n"))
            self.writestr(buf)
        if self._author:
            buf = "".join(("/Author (", self._author, ")\n"))
            self.writestr(buf)
        if self._keywords:
            buf = "".join(("/Keywords (", ' '.join(self._keywords), ")\n"))
            self.writestr(buf)
 
        if title:
            buf = "".join(("/Title (", title, ")\n"))
            self.writestr(buf)
 
        self.writestr(">>\n")
        self.writestr("endobj\n")
 
        self._locations[2] = self._fpos
 
        self.writestr("2 0 obj\n")
        self.writestr("<<\n")
        self.writestr("/Type /Catalog\n")
        self.writestr("/Pages 3 0 R\n")
        self.writestr(">>\n")
        self.writestr("endobj\n")
 
        self._locations[4] = self._fpos
        self.writestr("4 0 obj\n")
        self.writestr("<<\n")
        buf = "".join(("/BaseFont ", str(self._font),
                       " /Encoding /WinAnsiEncoding /Name /F1 /Subtype /Type1 /Type /Font >>\n"))
        self.writestr(buf)
 
        if self._IsoEnc:
            self.writestr(ENCODING_STR)
 
        self.writestr(">>\n")
        self.writestr("endobj\n")
 
        self._locations[5] = self._fpos
 
        self.writestr("5 0 obj\n")
        self.writestr("<<\n")
        self.writestr("  /Font << /F1 4 0 R >>\n")
        self.writestr("  /ProcSet [ /PDF /Text ]\n")
        self.writestr(">>\n")
        self.writestr("endobj\n")
 
    def startpage(self):
        """ Start a page of data """
 
        self._pageNo += 1
        self._curobj += 1
 
        self._locations.append(self._fpos)
        self._locations[self._curobj] = self._fpos
 
        self._pageObs.append(self._curobj)
        self._pageObs[self._pageNo] = self._curobj
 
        buf = "".join((str(self._curobj), " 0 obj\n"))
 
        self.writestr(buf)
        self.writestr("<<\n")
        self.writestr("/Type /Page\n")
        self.writestr("/Parent 3 0 R\n")
        self.writestr("/Resources 5 0 R\n")
 
        self._curobj += 1
        buf = "".join(("/Contents ", str(self._curobj), " 0 R\n"))
        self.writestr(buf)
        self.writestr(">>\n")
        self.writestr("endobj\n")
 
        self._locations.append(self._fpos)
        self._locations[self._curobj] = self._fpos
 
        buf = "".join((str(self._curobj), " 0 obj\n"))
        self.writestr(buf)
        self.writestr("<<\n")
 
        buf = "".join(("/Length ", str(self._curobj + 1), " 0 R\n"))
        self.writestr(buf)
        self.writestr(">>\n")
        self.writestr("stream\n")
        strmPos = self._fpos
 
        self.writestr("BT\n")
        buf = "".join(("/F1 ", str(self._ptSize), " Tf\n"))
        self.writestr(buf)
        buf = "".join(("1 0 0 1 50 ", str(self._pageHt - 40), " Tm\n"))
        self.writestr(buf)
        buf = "".join((str(self._vertSpace), " TL\n"))
        self.writestr(buf)
 
        return strmPos
 
    def endpage(self, streamStart):
        """End a page of data """
 
        self.writestr("ET\n")
        streamEnd = self._fpos
        self.writestr("endstream\n")
        self.writestr("endobj\n")
 
        self._curobj += 1
        self._locations.append(self._fpos)
        self._locations[self._curobj] = self._fpos
 
        buf = "".join((str(self._curobj), " 0 obj\n"))
        self.writestr(buf)
        buf = "".join((str(streamEnd - streamStart), '\n'))
        self.writestr(buf)
        self.writestr('endobj\n')
 
    def writepages(self):
        """Write pages as PDF"""
 
 
        beginstream = 0
        lineNo, charNo = 0, 0
        ch, column = 0, 0
        padding, i = 0, 0
        atEOF = 0
        linebuf = ''
 
        while not atEOF:
            beginstream = self.startpage()
            column = 1
 
            while column <= self._columns:
                column += 1
                atFF = 0
                atBOP = 0
                lineNo = 0
                # Special flag for regexp page break
                pagebreak = False
 
                while lineNo < self._lines and not atFF and not atEOF and not pagebreak:
                    linebuf = ''
                    lineNo += 1
                    self.writestr("(")
                    charNo = 0
 
                    while charNo < self._cols:
                        charNo += 1
                        ch = self._ifs.read(1)
                        cond = ((ch != '\n') and not(
                            ch == FF and self._doFFs) and (ch != ''))
                        if not cond:
                            # See if this dude matches the pagebreak regexp
                            if self._pagebreakre and self._pagebreakre.search(linebuf.strip()):
                                pagebreak = True
 
                            linebuf = ''
                            break
                        else:
                            linebuf = linebuf + ch
 
                        if ord(ch) >= 32 and ord(ch) <= 127:
                            if ch == '(' or ch == ')' or ch == '\\':
                                self.writestr("\\")
                            self.writestr(ch)
                        else:
                            if ord(ch) == 9:
                                padding = self._tab - \
                                    ((charNo - 1) % self._tab)
                                for i in range(padding):
                                    self.writestr(" ")
                                charNo += (padding - 1)
                            else:
                                if ch != FF:
                                    # write \xxx form for dodgy character
                                    buf = "".join(('\\', ch))
                                    self.writestr(buf)
                                else:
                                    # dont print anything for a FF
                                    charNo -= 1
 
                    self.writestr(")'\n")
                    if ch == FF:
                        atFF = 1
                    if lineNo == self._lines:
                        atBOP = 1
 
                    if atBOP:
                        pos = 0
                        ch = self._ifs.read(1)
                        pos = self._ifs.tell()
                        if ch == FF:
                            ch = self._ifs.read(1)
                            pos = self._ifs.tell()
                        # python's EOF signature
                        if ch == '':
                            atEOF = 1
                        else:
                            # push position back by one char
                            self._ifs.seek(pos - 1)
 
                    elif atFF:
                        ch = self._ifs.read(1)
                        pos = self._ifs.tell()
                        if ch == '':
                            atEOF = 1
                        else:
                            self._ifs.seek(pos - 1)
 
                if column < self._columns:
                    buf = "".join(("1 0 0 1 ",
                                   str((self._pageWd / 2 + 25)),
                                   " ",
                                   str(self._pageHt - 40),
                                   " Tm\n"))
                    self.writestr(buf)
 
            self.endpage(beginstream)
 
    def writerest(self):
        """Finish the file"""
 
        self._locations[3] = self._fpos
 
        self.writestr("3 0 obj\n")
        self.writestr("<<\n")
        self.writestr("/Type /Pages\n")
        buf = "".join(("/Count ", str(self._pageNo), "\n"))
        self.writestr(buf)
        buf = "".join(
            ("/MediaBox [ 0 0 ", str(self._pageWd), " ", str(self._pageHt), " ]\n"))
        self.writestr(buf)
        self.writestr("/Kids [ ")
 
        for i in range(1, self._pageNo + 1):
            buf = "".join((str(self._pageObs[i]), " 0 R "))
            self.writestr(buf)
 
        self.writestr("]\n")
        self.writestr(">>\n")
        self.writestr("endobj\n")
 
        xref = self._fpos
        self.writestr("xref\n")
        buf = "".join(("0 ", str((self._curobj) + 1), "\n"))
        self.writestr(buf)
        buf = "".join(("0000000000 65535 f ", str(LINE_END)))
        self.writestr(buf)
 
        for i in range(1, self._curobj + 1):
            val = self._locations[i]
            strval = str(val)
            buf = "".join((strval.zfill(10),
                           " 00000 n ", str(LINE_END)))
            self.writestr(buf)
 
        self.writestr("trailer\n")
        self.writestr("<<\n")
        buf = "".join(("/Size ", str(self._curobj + 1), "\n"))
        self.writestr(buf)
        self.writestr("/Root 2 0 R\n")
        self.writestr("/Info 1 0 R\n")
        self.writestr(">>\n")
 
        self.writestr("startxref\n")
        buf = "".join((str(xref), "\n"))
        self.writestr(buf)
        self.writestr("%%EOF\n")
 
 
def main():
 
    pdfclass = PyText2Pdf("Text.txt", "test.pdf")
    pdfclass.convert()
 
if __name__ == "__main__":
    main()