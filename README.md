# Foreign Language Vocab Helper
This is a Python program for finding words you don't know in a foreign language text. It keeps track of the words you do know and gives you a list of the ones you don't. It works for German, Spanish, and English.

## Installation

You need to have Python 3 installed. On linux, run the program with the path to the .txt or .srt file you want to parse:

```bash
python3 flvh.py -f ~/path/to/my_file.txt
```

## Usage

You should probably start by running it with a text file of the most common x words in your target language, so that it excludes the words you already know. For example, find a list of the most common 1000 words in German and run that.

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License
[GPL-3.0](https://choosealicense.com/licenses/gpl-3.0/)
