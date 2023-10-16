# AUTOGENERATED! DO NOT EDIT! File to edit: ../00_tools.ipynb.

# %% auto 0
__all__ = ['pd_timestamp', 'get_env', 'get_image_from_url', 'get_image', 'kill', 'get_hash_folder', 'save_selected_cities',
           'save_location_dicts', 'get_top_n_countries', 'ls', 'path_info', 'rm_r', 'search_notebooks',
           'df_chunk_generator', 'docker_container', 'LogDBHandler', 'get_logger', 'read_image_from_url',
           'compound_return', 'copy_func', 'patch_to', 'patch', 'to_pickle', 'from_pickle', 'telegram', 'pdrows',
           'pd_highlight', 'inline', 'plot_map', 'htop', 'get_proxies', 'append_csv', 'repeat_df', 'to_sql',
           'timestamp2int', 'startEndTimestamp', 'pd_set_float', 'plot_multiple_y', 'sql_head', 'make_clickable',
           'save_str2file', 'get_api_key']

# %% ../00_tools.ipynb 1
from pathlib import Path
import pandas as pd
import requests
import os
import logging
import psutil
import hashlib
from PIL import Image
import requests
import numpy as np
import sys

# %% ../00_tools.ipynb 2
def get_env():
    sp = sys.path[1].split("/")
    if "envs" in sp:
        return sp[sp.index("envs") + 1]
    else:
        return ""

# %% ../00_tools.ipynb 3
##depricated
def get_image_from_url(url,path = None):
    if url: response = requests.get(url, stream=True)
    if path: pass
    return Image.open(response.raw)

# %% ../00_tools.ipynb 4
def get_image(url= None,path = None):
    if url: response = requests.get(url, stream=True)
    if path: pass
    else:    path = response.raw
    return Image.open(path)

# %% ../00_tools.ipynb 5
def kill(kill_procs     =['photos_resize','scrape','photos_save','0_app']):
    kill_command       = lambda x : os.system(f'pkill -f {x}')
    [kill_command(p) for p in kill_procs]

# %% ../00_tools.ipynb 6
def get_hash_folder(id):
    return hashlib.sha1(f'{id}'.encode('utf-8')).hexdigest()[:2]

# %% ../00_tools.ipynb 7
def save_selected_cities():
        q = """select l.id, c.country,c.city from listings l
                join listings_cities c on (l.id = c.listing_id) """
        df = pd.read_sql(q,engine)
        r = df.groupby('city')['id'].count().sort_values().to_frame().sort_values('id',ascending=False)
        r= r.reset_index().merge(df.drop_duplicates('city')[['country','city']],on='city')
        r = r[~r.country.isin(['Russia','Ukraine'])]
        r.to_csv('selected_cities.csv',index=False)

# %% ../00_tools.ipynb 8
def save_location_dicts():
    cities_df = pd.read_sql('select city, country from cities',engine)
    countries = cities_df[['country']].drop_duplicates().sort_values('country').reset_index(drop=True)['country']
    cities = cities_df.sort_values(['country','city']).drop_duplicates().reset_index(drop = True)
    cities = cities['country'] + ', ' + cities['city']

    city_replace_dict    = {value:key for key, value in cities.to_dict().items()}
    country_replace_dict = {value:key for key, value in countries.to_dict().items()}
    to_pickle((city_replace_dict,country_replace_dict),'location_dicts.pkl')

# %% ../00_tools.ipynb 9
def get_top_n_countries(n):
    return pd.read_sql("""select country, count(*)
                from photos p
                join listings l on        (l.id = p.listing_id)
                join listings_cities c on (c.listing_id = l.id)
                group by country""",engine).sort_values('count',ascending=False).head(n).sort_values('country').country.values

# %% ../00_tools.ipynb 10
def ls(self,limit=10**10):
    paths = []
    it = self.iterdir()
    for _ in range(limit):
        try:
            paths.append(next(it))
        except StopIteration:
            break
    return paths
Path.ls = ls

# %% ../00_tools.ipynb 11
def path_info(path,limit=10**10):
    path = path.ls(limit) if path.is_dir() else path
    files = pd.DataFrame([[f,
                           f.name,
                           pd.Timestamp(f.stat().st_ctime,unit='s'),
                           f.stat().st_size]
                           for f in path],
                           columns=['path','name','time','size']) #if is a directory
    files['size']=(files['size']/10**6)
    return files.sort_values('time')

# %% ../00_tools.ipynb 12
from typing import Union

def rm_r(target: Union[Path, str], only_if_empty: bool = False):
    """
    Delete a given directory and its subdirectories.

    :param target: The directory to delete
    :param only_if_empty: Raise RuntimeError if any file is found in the tree
    """
    target = Path(target).expanduser()
    if not  target.is_dir(): 
        print (target, ' is not a directory')
        return
    for p in sorted(target.glob('**/*'), reverse=True):
        if not p.exists():
            continue
        p.chmod(0o666)
        if p.is_dir():
            p.rmdir()
        else:
            if only_if_empty:
                raise RuntimeError(f'{p.parent} is not empty!')
            p.unlink()
    target.rmdir()

# %% ../00_tools.ipynb 13
def search_notebooks(kword,path=None):
    if not path: return os.popen(                 f"grep --include='*.ipynb' --exclude-dir='.ipynb_checkpoints' -rliw . -e '{kword}'").read().split('\n')
    if  path:    return os.popen(f"cd; cd {path};   grep --include='*.ipynb' --exclude-dir='.ipynb_checkpoints' -rliw . -e '{kword}'").read().split('\n')

# %% ../00_tools.ipynb 14
def df_chunk_generator(df,chunksize,shuffle=False):
    if shuffle: df=df.sample(frac=1)
    start,stop = 0,chunksize
    for i in range(start,len(df),chunksize):
        chunk = df.iloc[start:stop]
        start+=chunksize
        stop +=chunksize
        yield chunk

# %% ../00_tools.ipynb 16
def docker_container(name):
    import docker
    client = docker.from_env()
    return [c for c in client.containers.list(all=True) if c.attrs['Name'] == f'/{name}'][0]

# %% ../00_tools.ipynb 17
class LogDBHandler(logging.Handler):

    def __init__(self,engine,sql_table,schema):
        self.engine,self.sql_table,self.schema = engine,sql_table,schema
        logging.Handler.__init__(self)

    def emit(self, record):
        df = pd.DataFrame(record.msg,index = [0])
        df['level_no'] = record.levelname
        df['timestamp'] = pd.Timestamp.utcnow()
        df.to_sql(self.sql_table,self.engine,if_exists='append',index=False,schema = self.schema)

# %% ../00_tools.ipynb 18
def get_logger(engine,sql_table,schema,return_handler=False):
    logger = logging.getLogger('main')
    logger.setLevel(logging.DEBUG)
    bd_handler = LogDBHandler(engine,sql_table,schema)
    logger.addHandler(bd_handler)
    if return_handler: return logger,bd_handler
    else:              return logger

# %% ../00_tools.ipynb 19
def read_image_from_url(url=None):
    response = requests.get(url, stream=True)
    return Image.open(response.raw)

# %% ../00_tools.ipynb 20
def compound_return(r,n): return ((1+r)**n)-1

# %% ../00_tools.ipynb 21
import functools
from types import FunctionType

def copy_func(f):
    "Copy a non-builtin function (NB `copy.copy` does not work for this)"
    if not isinstance(f,FunctionType): return copy(f)
    fn = FunctionType(f.__code__, f.__globals__, f.__name__, f.__defaults__, f.__closure__)
    fn.__dict__.update(f.__dict__)
    return fn
def patch_to(cls, as_prop=False):
    "Decorator: add `f` to `cls`"
    if not isinstance(cls, (tuple,list)): cls=(cls,)
    def _inner(f):
        for c_ in cls:
            nf = copy_func(f)
            # `functools.update_wrapper` when passing patched function to `Pipeline`, so we do it manually
            for o in functools.WRAPPER_ASSIGNMENTS: setattr(nf, o, getattr(f,o))
            nf.__qualname__ = f"{c_.__name__}.{f.__name__}"
            setattr(c_, f.__name__, property(nf) if as_prop else nf)
        return f
    return _inner

def patch(f):
    "Decorator: add `f` to the first parameter's class (based on f's type annotations)"
    cls = next(iter(f.__annotations__.values()))
    return patch_to(cls)(f)

# %% ../00_tools.ipynb 22
def to_pickle (obj, file_name):
    import pickle
    file = open(file_name, 'wb')
    # dump information to that file
    pickle.dump(obj, file, protocol=4)
    # close the file
    file.close()

def from_pickle (file_name):
#     print(f'unpickling {file_name} ')
    import pickle
    file = open(file_name, 'rb')
    # dump information to that file
    return pickle.load(file)
    # close the file
    file.close()

# %% ../00_tools.ipynb 23
def telegram(bot_message):
    import requests
#     proxies_list = get_proxies()

#     proxies = {'https': proxies_list[0]}

    bot_token = '918570679:AAHGf8qed65479rj35M3uQ9oVS4rxuD2xrs'
    bot_chatID = '78882798'
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message

    response = requests.get(send_text)#, proxies=proxies)

    return response.json()

# %% ../00_tools.ipynb 24
def pdrows(n):
    pd.options.display.max_rows=n
    pd.options.display.min_rows=n

# %% ../00_tools.ipynb 25
def pd_highlight(df,v):
    def highlight(s,v):
        match = s == v
        return ['background-color: yellow' if v else '' for v in match]
    return df.style.apply(highlight, args=(v,),axis=1)

# %% ../00_tools.ipynb 26
#launch in the background
def inline(func,args=None):
    import threading
    if not args: thread = threading.Thread(target=func)
    else:        thread = threading.Thread(target=func, args=args)
    thread.start()

# %% ../00_tools.ipynb 27
def plot_map(df, sample=10000, **kwargs):
    import plotly.express as px
    if    sample >len(df):pass
    else: df =df.sample(sample)
    if 'lon' not in df.columns: df['lon'],df['lat'] = df.geometry.x,df.geometry.y
    px.set_mapbox_access_token(mapbox_access_token)
    return px.scatter_mapbox(df, lat='lat', lon='lon', **kwargs)

# %% ../00_tools.ipynb 28
def htop():
    htop = pd.DataFrame([proc.as_dict() for proc in psutil.process_iter()])
   # htop = htop[htop['username']=='dima']
    htop['create_time'] = pd.to_datetime(htop['create_time'],unit='s')
    htop = htop[htop['memory_percent']>0]
    htop = htop[htop['name']=='python']
    htop['kernel'] = htop['cmdline'].apply(lambda x:x[-1])
    htop =htop.sort_values('create_time',ascending=False)
    return htop[['pid','kernel','num_threads','memory_percent','create_time','open_files','cpu_percent','status']]

# %% ../00_tools.ipynb 29
def get_proxies():
    proxies = pd.read_csv('/home/dima/data/proxy.txt')
    proxies.columns = ['prixies']
    proxies = proxies['prixies'].tolist()
    proxies = [line.strip().split(':') for line in open("/home/dima/data/proxy.txt", "r").readlines()]
    return [f'http://{proxy[2]}:{proxy[3]}@{proxy[0]}:{proxy[1]}' for proxy in proxies]

# %% ../00_tools.ipynb 30
def append_csv(name, **kwargs):
    with open(name, 'a') as f:
        writer = csv.writer(f)
        writer.writerow(kwargs.keys())
        writer.writerow(kwargs.values())

# %% ../00_tools.ipynb 31
def repeat_df(df,times):
    df_dtypes = df.dtypes
    df_cols = df.columns
    df = pd.DataFrame(np.repeat(df.values,times,axis=0))
    df.columns = df_cols
    df = df.astype(df_dtypes)
    return df

# %% ../00_tools.ipynb 32
def to_sql(df,table,chunksize=None):
    if chunksize: df.to_sql(table,engine,method='multi',if_exists='append',chunksize=chunksize,index=False)
    else: df.to_sql(table,engine,method='multi',if_exists='append',index=False)

# %% ../00_tools.ipynb 33
def timestamp2int(timestamp = pd.Timestamp.now()):
    timestamp = pd.Timestamp(timestamp)
    return int(int(timestamp.to_numpy())/10**6)

# %% ../00_tools.ipynb 34
pd_timestamp = lambda timestamp:pd.to_datetime(timestamp,unit='ms',utc=True)

# %% ../00_tools.ipynb 35
def startEndTimestamp(length,shift = 0):
    end = pd.Timestamp.utcnow() - pd.Timedelta(f'{shift} days')
    return end - pd.Timedelta(f'{length} days'), end

# %% ../00_tools.ipynb 36
def docker_container(name):
    import docker
    client = docker.from_env()
    return [c for c in client.containers.list(all=True) if c.attrs['Name'] == f'/{name}'][0]

# %% ../00_tools.ipynb 37
def pd_set_float(points): pd.options.display.float_format = ('{:.'+f'{points}'+'f}').format

# %% ../00_tools.ipynb 38
import plotly.express as px
from plotly.subplots import make_subplots


def plot_multiple_y(*series):
    subfig = make_subplots(specs=[[{"secondary_y": True}]])
    fig = px.line(series[0])
    data = fig.data

    for s in series[1:]:
        fig2 = px.scatter(s,
                          color_discrete_map={
                          "rate": "green",
                          "rate_mean": "orange"})
        fig2.update_traces(yaxis="y2")
        data = data + fig2.data

    subfig.add_traces(data)
    subfig.show()

# %% ../00_tools.ipynb 39
def sql_head(table, limit=5):
    return pd.read_sql(f'select * from {table} limit {limit}',engine)

# %% ../00_tools.ipynb 40
def make_clickable(val):
    # target _blank to open new window
    return '<a target="_blank" href="{}">{}</a>'.format(val, val)

# %% ../00_tools.ipynb 41
def save_str2file(s,path):
    with open(Path(path), "wt") as f: f.write(s)

# %% ../00_tools.ipynb 42
def get_api_key(api_path,name):
    with open(api_path/f'{name}') as file: return file.read().strip()
    
