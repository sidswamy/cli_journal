#!/usr/bin/env python3
from pathlib import Path,PurePath
import subprocess, time, sqlite3, json, tempfile
import argparse

# Default configuration
journal_config = 0
con = 0
script_dir = 0

def load_config(conf_file:str):
    global journal_config
    path = Path(conf_file)
    try:
        if not path.is_file():
            print('INFO:\tConfig JSON file not found. Creating one with default values.')
            journal_config = {'dbname':'sid_journal.db','hash':''}
            with open(path,'w') as f:
                json.dump(journal_config,f,sort_keys=True,indent=4)
        else:
            with open(path,'r') as f:
                journal_config = json.load(f)
        return
    except Exception as e:
        print('ERROR:\tWhle loading config file.')
        raise e

def connect_db():
    path = Path(journal_config['dbname'])
    db_exists = path.is_file()

    global con
    con = sqlite3.connect(path)

    if not db_exists :
        print('INFO:\tDB file not found! I will create a blank one.')
        try:
            with con:
                con.execute(f'''
                create table journal(
                    jdate text primary key,
                    jupdated text,
                    jentry text
                );
                ''')
        except Exception as e:
            print('ERROR:\tWhile creating DB file and empty tables.')
            con.close
            raise e
    return

def check_entry():
    jdate = time.strftime('%F',time.localtime())
    try:
        with con:
            row = con.execute(f'select jentry from journal where jdate=(?)',(jdate,)).fetchone()
            if row != None:
                return row[0]
            else:
                return ''
    except Exception as e:
        print('ERROR:\tWhile checking for existing records.')
        raise e

def write_entry(old_entry=''):
    with tempfile.NamedTemporaryFile() as f:
        try:
            if not isinstance(old_entry,bytes):
                f.write(bytes(old_entry,'utf-8'))
            else:
                f.write(old_entry)
            f.flush()
            subprocess.run(['nano',f.name])
            f.seek(0)
            return f.read()
        except Exception as e:
            print('ERROR:\tWhile creating text file for journal entry.')
            raise e

def save_to_db(entry:str,isold:bool,jdate:str=''):
    if jdate == '':
        jdate = time.strftime('%F',time.localtime())
    jtime = time.strftime('%T',time.localtime())
    entry_row = (jdate,jtime,entry)

    try:
        with con:
            if not isold:
                con.execute(f'insert into journal values(?,?,?);',entry_row)
            else:
                con.execute(f'''
                update journal
                set
                jupdated = (?),
                jentry = (?)
                where
                jdate = (?)
                ;
                ''',(jtime,entry,jdate))
    except Exception as e:
        print('ERROR:\tWhile saving entry to DB.')
        raise e

def new_entry():
    try:
        old_entry = check_entry()
        entry = write_entry(old_entry)
        save_to_db(entry,bool(len(old_entry)))
        print('Entry saved. \U0001F609')
    except Exception as e:
        print('ERROR:\tEntry not saved because of following errors:\n')
        print(e)

def read_entry(jdate:str):
    try:
        jdate = jdate.strip()
        time.strptime(jdate,'%Y-%m-%d')
    except:
        print(f'Invalid date:\t{jdate}')
        return
    try:
        with con:
            row = con.execute(f'select * from journal where jdate=(?)',(jdate,)).fetchone()
            if row != None:
                print('=' * 50)
                print(f'Entry Date: {row[0].upper()}')
                print(f'Last Updated: {row[1].upper()}')
                print(f'Journal Entry:')
                print('-' * 50)
                
                if isinstance(row[2],str):
                    print(f'{row[2].strip()}')
                else:
                    print(f'{row[2].decode("utf-8").strip()}')
                print('=' * 50)
                
                return
            else:
                print(f'No entry found for {jdate}.')
    except Exception as e:
        print('ERROR:\tWhile reading entry.')
        raise e

def import_entry(import_params):
    path = Path(import_params[0])
    try:
        jdate = import_params[1].strip()
        time.strptime(jdate,'%Y-%m-%d')
    except:
        print(f'Invalid date:\t{jdate}')
        return
    if path.is_file():
        with open(path) as f:
            save_to_db(f.read().strip(),False,jdate)
            print('Entry imported successfully!')
    else:
        print(f'ERROR:\tFile <{import_params[0]}> not found!')

def load_config_and_connect():
    conf_name = 'jrnl_conf.json'
    if args.config:
        conf_name = args.config
        conf_file = conf_name
    else:
        script_dir = str(PurePath(__file__).parent)
        conf_file = ''.join([script_dir,'/',conf_name])
    load_config(conf_file)
    # journal_config['dbname'] = ''.join([script_dir,'/',journal_config['dbname']])
    connect_db()

def show_entry_dates():
    try:
        with con:
            rows = con.execute(f'select jdate from journal').fetchall()
            if rows != None:
                print('The database has entries for following dates:')
                for row in rows:
                    print(row[0])
                return
            else:
                print('No entries found. Seems like a new databse file.')
                return
    except Exception as e:
        print('ERROR:\tWhile reading entry.')
        raise e


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('-r','--read',metavar='date',help='Read journal entry for a date (ISO).')
    parser.add_argument('-c','--config',metavar='file',help='Config file. [Default: jrnl_conf.json]')
    parser.add_argument('-i','--import',dest='impt',nargs=2,metavar=('file','date'),help='Import entry from a filename for the specified date.')
    parser.add_argument('-s','--show',action='store_true',help='Show the list of dates with journal entries.')

    args = parser.parse_args()
    # print(args,'\n\n')

    load_config_and_connect()
    try:
        if args.read:
            read_entry(args.read)
        elif args.impt:
            import_entry(args.impt)
        elif args.show:
            show_entry_dates()
        else:
            new_entry()
    except Exception as e:
        print('ERROR:\tError encountered! There should be some information below:')    
        print(e)
