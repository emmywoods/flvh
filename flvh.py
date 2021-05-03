import sys, re, sqlite3, time, requests, bz2, os, requests, time, datetime, nltk, wikipedia, argparse


words = {}
SECONDS_PER_DAY = 86400
debug = False

'''Extract a .bz2 compressed file'''
def ExtractFile(uFilename, cFilename):
    try:
        with open(uFilename, 'wb') as txtFile, bz2.BZ2File(cFilename, 'rb') as bFile:
            for data in iter(lambda: bFile.read(100*1024), b''):
                txtFile.write(data)
    except:
        print('Error extracting file: ' + cFilename)
        sys.exit(2)

''' Downloads a file from URL, if it's not already in directory, and sends it to ExtractFile '''
def GetAndExtractFile(uFilename, cFilename, url, siteName):
    # maybe the file is already in the directory
    if os.path.exists(uFilename):
        return
    # or maybe it's been downloaded but not extracted
    elif os.path.exists(cFilename):
        ExtractFile(cFilename)
        return
    # no file, download it
    print('Getting ' + cFilename + ' file from ' + siteName + ', this may take some time')
    response = requests.get(url, stream = True)
    compressedFile = open(cFilename,"wb")
    for chunk in response.iter_content(chunk_size=1024):
        compressedFile.write(chunk)
    compressedFile.close()
    # and extract it
    ExtractFile(uFilename, cFilename)

'''Gets the sentences and links files for the correct language from Tatoeba, if needed'''
def GetFiles(language, nativeLanguage):
    # uFilename = uncompressed, cFilename = compressed
    lang = language
    # grab and decompress the Tatoeba files for both languages
    for x in range(2):
        uFilename = lang + '_sentences.tsv'
        cFilename = uFilename + '.bz2'
        url = 'https://downloads.tatoeba.org/exports/per_language/' + lang + '/' + lang + '_sentences.tsv.bz2'
        GetAndExtractFile(uFilename, cFilename, url, "Tatoeba")
        lang = nativeLanguage
    # grab and decompress the links file
    uFilename = 'links.csv'
    cFilename = 'links.tar.bz2'
    url = 'https://downloads.tatoeba.org/exports/links.tar.bz2'
    GetAndExtractFile(uFilename, cFilename, url, "Tatoeba")


''' Archives the old studyfile with a timestamp so it doesn't get overwritten. '''
def ArchiveFile(fileName):
    if not os.path.exists(fileName):
        return
    dot = fileName.rfind('.')
    if os.path.isfile(fileName):
        # move it so I don't overwrite the old file
        os.replace(fileName, fileName[:dot] + datetime.datetime.fromtimestamp(time.time()).strftime('%Y%m%d-%H%M%S') + fileName[dot:])
        

'''Creates a sentence file in the correct format for usage with Clozemaster'''
class CreateStudyFile():

    def __init__(self, language, nativeLanguage, apiKey, c, conn):
        self.fSentences = {}
        self.links = {}
        self.maxPerWord = 1
        # words dict may have a huge number of already known words in it, only need new words
        self.newWords = {key: self.maxPerWord for key, value in words.items() if value > 0}
        self.ignoredWords = []
        self.language = language
        self.nativeLanguage = nativeLanguage
        self.fFile = language + '_sentences.tsv'
        self.nFile = nativeLanguage + '_sentences.tsv'
        self.lFile = 'links.csv'
        self.clozefile = 'clozefile.tsv'
        self.apiKey = apiKey
        self.sentencesWritten = 0
        self.c = c
        self.conn = conn
   
    '''Pass through the file of foreign sentences and find sentences with the target words.
       Put them into self.fSentences '''
    def parseForeignFile(self):
        with open(self.fFile, 'r') as foreignF:
            for fLine in foreignF:
                fid, fSentence = int(fLine.split('\t')[0]), fLine.split('\t')[2][:-1]
                for key in self.newWords:
                    if self.newWords[key] > 0:
                        m = re.search(rf'\b{key}\b', fSentence, re.IGNORECASE)
                        if m:
                            self.fSentences[fid] = fSentence + '\t' + key 
                            self.newWords[key] -= 1
                            break # I don't want the same sentence for multiple words

    ''' Finds id numbers for native sentences that match the foreign sentences in self.fSentences.
        It puts matching native and foreign id's into the self.links dict.
        The native id's are not necessarily for the right native language. '''
    def parseLinksFile(self):
        with open(self.lFile, 'r') as linksF:
            lLine = next(linksF)
            # split lLine into links foreign id and links native id
            lfid, lnid = 0, 0 # lLine.split('\t')[0], lLine.split('\t')[1]
            for key, sentence in self.fSentences.items():
                while (key > lfid):
                    #get next item from links file
                    try:
                        lLine = next(linksF)
                    except StopIteration as e:
                        return
                    lfid, lnid = int(lLine.split('\t')[0]), int(lLine.split('\t')[1])
                while (key == lfid):
                    self.links[lnid] = lfid
                    try:
                        lLine = next(linksF)
                    except StopIteration as e:
                        return
                    lfid, lnid = int(lLine.split('\t')[0]), int(lLine.split('\t')[1])
        # sort self.links by key so the native sentence numbers are in order
        self.links = {k: self.links[k] for k in sorted(self.links)}

    ''' Pass through the file of native language sentences and find translations for sentences that
        were identified by parseForeignFile as having target words in them. '''
    def parseNativeFile(self):
        with open (self.nFile, 'r') as nativeF: 
            nLine = next(nativeF)
            nid, nSentence = 0, ''
            for nKey, fKey in self.links.items(): 
                while (nKey > nid):
                    try:
                        nLine = next(nativeF)
                    except StopIteration as e:
                        return
                    nid, nSentence = int(nLine.split('\t')[0]), nLine.split('\t')[2][:-1]
                if (nKey == nid):
                    # this is a match between a native sentence and a foreign sentence
                    # add it to the sentences file
                    with open(self.clozefile, 'a+') as cf:
                        cf.write('"' + self.fSentences[fKey].split('\t')[0] + '"' + '\t' + '"' + nSentence + '"' + '\t' + self.fSentences[fKey].split('\t')[1] + '\n')
                        self.sentencesWritten += 1
                        
    ''' refineNewWordsDict removes words from self.newWords that already have at least one matching sentence.'''
    def refineNewWordsDict(self):
        self.newWords = {key: self.maxPerWord for key, value in self.newWords.items() if value == self.maxPerWord}

    ''' Checks wikipedia articles for the specified key and returns a suitable sentence if found. '''
    def wikiSearch(self, titles, key, depth):
        global debug
        if depth > 2:
            ''' This is to avoid getting stuck in an endless loop if there are disambiguation pages
                that point to each other '''
            return ''
        sentence = ''
        if debug:
            print('titles ' + str(titles))
        for t in titles:
            if debug:
                print('checking ' + t)
            try:
                article = wikipedia.page(t)
                content = [line for line in article.content.split('\n') if line != '' and line[0] != '=']
                for chunk in content:
                    sentenceList = nltk.tokenize.sent_tokenize(chunk)
                    for s in sentenceList:
                        if re.search(key, s, re.IGNORECASE):
                            # this is a suitable (hopefully) sentence in the target language.
                            return s
            except wikipedia.DisambiguationError as e:
                # disambig error includes a list of actual page titles, use that as a list of titles
                sentence = self.wikiSearch(e.options, key, depth+1)
                if sentence != '':
                    return sentence
            except:
                if debug == True:
                    e = sys.exc_info()[0]
                    print("Error on word " + key + ", title " + t + "   " + str(e))
        return sentence


    ''' Searches wikipedia api to find titles of articles containing a word that doesn't yet have a sentence '''
    def getOneSentenceForWord(self, key):
        try:
            titles = wikipedia.search(key)
            if len(titles) > 0:
                return self.wikiSearch(titles, key, 0)
        except:
            e = sys.exc_info()[0]
            print("Error on word " + key + str(e))
            return
        return '' # didn't find a sentence

    ''' translateSentence uses the Google translate api to get a translation for one sentence. '''
    def translateSentence(self, sentence):
        if self.apiKey == None:
            print("Unable to get translations from Google translate, no API key.")
            return '' # can't attempt to get a translation
        url = ('https://translation.googleapis.com/language/translate/v2?'
               'q=' + sentence + '&'
               'target=' + self.nativeLanguage[:2] + '&'
               'source' + self.language[:2] + '&'
               'key=' + self.apiKey)
        try:
            r = requests.get(url).json()
        except:
            e = sys.exc_info()[0]
            print("Error: " + str(e))
            print("Unable to get a translation for: ")
            print(sentence)
            return ''
        return r['data']['translations'][0]['translatedText']

    ''' In actual foreign language texts, most words that aren't in the Tatoeba files
        are not actually real words in the language. What's left is mostly names, words in other languages,
        and misspellings. Filtering out words that aren't in a dictionary in the target language
        would be ideal, but this function is checking whether a word has a translation that is
        different from the word being translated. This filters out most non-words.
        Google translate silently corrects some misspellings before translating though. '''
    def filterNonwords(self):
        realWords = []
        for w in self.newWords:
            if self.translateSentence(w).lower() == w:
                self.ignoredWords.append(w)
            else:
                realWords.append(w)
        self.newWords = {key: self.maxPerWord for key in realWords}
        if len(self.ignoredWords) > 0:
            print("probable non-words that are being ignored: ")
            print(str(self.ignoredWords))
        return

    ''' findSentencesFromApi attempts to find a suitable sentence for words that aren't in the Tatoeba file.
        It searches Wikipedia using the wikipedia API. '''
    def findSentencesFromApi(self):
        global debug
        # at this point, any remaining words in the words dict don't have a match in the tatoeba file
        # so need to find a matching sentence elsewhere
        self.refineNewWordsDict() # remove words that were found in Tatoeba file
        self.filterNonwords() # remove most non-words
        if debug == True:
            print(str(len(self.newWords)) + ' words remain after checking Tatoeba files.')
        wikipedia.set_rate_limiting(True)
        wikipedia.set_lang(self.language[:2])
        for key in self.newWords:
            sentence = self.getOneSentenceForWord(key)
            if sentence != '':
                self.newWords[key] -= 1
                # get a translation
                translatedSentence = self.translateSentence(sentence)                
                with open(self.clozefile, 'a+') as cf:
                    cf.write('"' + sentence + '"' + '\t' + '"' + translatedSentence + '"' + '\t' + key + '\n')
                    self.sentencesWritten += 1

    ''' Print message explaining what was accomplished. '''
    def printSummary(self):
        if self.sentencesWritten > 0:
            print('Wrote ' + str(self.sentencesWritten) + ' sentences to ' + self.clozefile)
        else:
            print('Did not find any new sentences to write.')

    ''' Print any words that don't have sentences. '''
    def printRemainingWords(self):
        self.refineNewWordsDict()
        if len(self.newWords) > 0:
            print ('\nCould not find sentences for the following ' + str(len(self.newWords)) + ' words:')
            for key in self.newWords:
                if key != "":
                    print(key)

    ''' Remove these words from the words database because they couldn't be added to the study file
        and they may be real words. '''
    def removeRemaining(self):
        for w in self.newWords:
            DeleteWordFromDB(self.c, self.conn, w)

def AddWordToDB(c, conn, strippedWord, timestamp, inputfile):
    c.execute('REPLACE INTO words VALUES (?, ?, ?)', (strippedWord, timestamp, inputfile))
    conn.commit()

def DeleteWordFromDB(c, conn, word):
    c.execute("DELETE FROM words WHERE word='" + word + "'")
    conn.commit()
        
''' ParseFile finds all the new words in a file that aren't already in the database.
    It adds new words to the database.'''
def ParseFile(c, conn, inputfile, days=None):
    global words
    # make a timestamp for insertions from this file.
    # every word from the same file will have the same timestamp to make it easy
    # to delete or ignore all words added from a file
    timestamp = int(time.time())
    with open(inputfile,'r') as file:
        for line in file:        
            for word in line.split(): 
                # strip numbers, punctuation, etc characters
                strippedWord = re.sub('[^A-Za-z\u00C0-\u024F]+', '', word).lower()
                if strippedWord in words:
                    if words[strippedWord] > 0:
                        words[strippedWord] += 1
                else:
                    query = "SELECT * FROM words WHERE word='" + strippedWord + "'"
                    if days is not None:
                        query += "AND timestamp >= " + str(timestamp - (SECONDS_PER_DAY * days))
                    c.execute(query)
                    if c.fetchone() is None:
                        words[strippedWord] = 1
                        AddWordToDB(c, conn, strippedWord, timestamp, inputfile)
                    else:
                        # the word is already known, put it into words with a value of -1 to ignore it
                        # so that the database isn't repeatedly queried on this word
                        words[strippedWord] = -1

'''Displays new words sorted by frequency in the processed text'''
def DisplaySorted():
    sortedWords = {k: v for k, v in sorted(words.items(), key=lambda item: item[1])}
    for key in sortedWords:
        if key != "" and sortedWords[key] > 0:
            print(key)
            #print(sortedWords[key], '  ', key)

''' Attempts to setup a SQLite database to store already known words in.
    This function also downloads the nltk sentence tokenizer.'''
def DatabaseSetup(dbFilename):
    conn = sqlite3.connect(dbFilename)
    c = conn.cursor()
    try:
        c.execute('''CREATE TABLE words
            (word TEXT PRIMARY KEY NOT NULL, timestamp INTEGER, inputfile TEXT)''')
        # nltk needs this, and I'm putting it here because it only needs to run once
        nltk.download('punkt')
    except:
        pass
        # if the table already exists, that's fine
    return c, conn


def main(args):
    global debug

    if args.debug:
        debug = True

    if args.trash:
        ArchiveFile(args.db_file)
    
    c, conn = DatabaseSetup(args.db_file)
    ParseFile(c, conn, args.file)
    #DisplaySorted()

    if args.no_study_file:
        DisplaySorted()
    else:
        GetFiles(args.language, args.native_language)
    
        sf = CreateStudyFile(args.language, args.native_language, args.api_key, c, conn)

        ArchiveFile(sf.clozefile)
        sf.parseForeignFile()
        sf.parseLinksFile()
        sf.parseNativeFile()
        if args.api_key != None:
            sf.findSentencesFromApi()
        sf.printSummary()
        sf.printRemainingWords()
        sf.removeRemaining()

    conn.close()

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Find new words in a text file and create a study file with sentences containing those words.")

    parser.add_argument('-f', '--file', required=True,
                        help="File name of the file to parse for new words")
    parser.add_argument('-l', '--language', required=True,
                        help="Foreign language 3-letter abbreviation")
    parser.add_argument('-n', '--native_language', default='eng',
                        help="Native language 3-letter abbreviation")
    parser.add_argument('-k', '--api_key', default=None,
                        help="Words that aren't found in the Tatoeba sentences may be searched for with the Wikipedia API and a translation is taken from Google Translate if there is a Google API key available.")
    parser.add_argument('--no_study_file', action='store_true',
                        help="Don't find sentences or create a study file. Prints a list of unknown words.")
    parser.add_argument('--db_file', default="words.db",
                        help="Specify database file name.")
    parser.add_argument('-d', '--debug', action='store_true',
                        help="Show extra output for debugging")
    parser.add_argument('-t', '--trash', action='store_true',
                        help="Trash the words database! (Actually archives the file)")
    
    args = parser.parse_args()
    main(args)
    
    
