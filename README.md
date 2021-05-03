# Foreign Language Vocab Helper
This is a Python program for finding words you don't know in a foreign language text. It creates a study file that's compatible with Clozemaster with sentences for studying the words you don't know. It keeps track of the words you do know and only finds sentences for the ones you don't.

## Installation

You need to have Python 3 installed. Install dependencies with:

```bash
pip install -r requirements.txt
```

On linux, run the program with the path to the .txt or .srt file you want to parse.

## Usage

You should probably start by running it with a text file of the most common x words in your target language, so that it excludes the words you already know. For example, find a list of the most common 1000 words in German and run that.

```bash
python3 flvh.py -f ~/path/to/my_file.txt -l language
```


