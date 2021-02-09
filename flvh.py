import sys, getopt, re, sqlite3, time

words = {}
inputfile = ''
conn = sqlite3.connect('words.db')

def ParseFile(c):
    global words, inputfile, conn
    # make a timestamp for insertions from this file.
    # every word from the same file will have the same timestamp to make it easy
    # to delete or ignore all words added from a file
    timestamp = int(time.time())
    with open(inputfile,'r') as file:
        for line in file:        
            for word in line.split(): 
                # strip special characters
                strippedWord = re.sub('[^A-Za-zÄäÖöÜüẞßÁáÉéÍíÓóÚúÑñ]+', '', word).lower()
                if strippedWord in words:
                    if words[strippedWord] > 0:
                        words[strippedWord] += 1
                else:
                    c.execute('SELECT * FROM words WHERE word=?', (strippedWord,))
                    if c.fetchone() is None:
                        words[strippedWord] = 1
                        c.execute('INSERT INTO words VALUES (?, ?, ?)', (strippedWord, timestamp, inputfile))
                        conn.commit()
                    else:
                        # the word is already known, put it into words with a value of -1 to ignore it
                        # so that the database isn't repeatedly queried on this word
                        words[strippedWord] = -1

def DisplaySorted():
    sortedWords = {k: v for k, v in sorted(words.items(), key=lambda item: item[1])}
    for key in sortedWords:
        if key != "" and sortedWords[key] > 0:
            print(key)
            #print(sortedWords[key], '  ', key)

def ProcessArgs():
    global inputfile
    argv = sys.argv[1:]
    try:
        opts, args = getopt.getopt(argv, "f:s:")
    except getopt.GetoptError:
        #put some help here?
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-f':
            inputfile = arg
	
def DatabaseSetup():
    global conn
    c = conn.cursor()
    try:
        c.execute('''CREATE TABLE words
             (word TEXT PRIMARY KEY NOT NULL, timestamp INTEGER, inputfile TEXT)''')
    except:
        pass
        # if the table already exists, that's fine
    return c

def main():
    global conn
    c = DatabaseSetup()

    ProcessArgs()
    ParseFile(c)
    DisplaySorted()

    conn.close()

if __name__ == "__main__":
    main()
    
