import pafy
import yt_connect as ytc
import config.creds as creds
import json
import os, sys, errno
import hashlib
from pprint import pprint
from datetime import datetime

'''TODO:
		- really need a better approach to logging the differences between downloads, jeez'''

_BASE = 'https://www.youtube.com/'
_VID_PATH = 'watch?v='
_PL_PATH = 'playlist?list='
_STORE_PATH = './videos'
_LAST_SAVE_FILE = './videos/last.json'

_SAVE_FILE = 'dl.json'
_DT_FORMAT = '%Y%m%d%H%M%S'

def add_index(playlist_data):
	pl_count = 1
	for i in playlist_data['items']:
		i['add_order'] = pl_count
		pl_count += 1
	return playlist_data

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python > 2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

def getPlaylistData(playlist=creds.YOUTUBE_PL):
	playlist_url = _BASE+_PL_PATH+playlist
	playlist_data = pafy.get_playlist(playlist_url)
	return add_index(playlist_data)

def getDirData(path=_STORE_PATH):
	'''returns a dictionary of information about the current directory storing the downloaded videos'''
	res = []
	dirData = {}

	for r,d,f in os.walk(path):
		res.append(d)

	ids = [i[0] for i in res[1:] if len(i) is not 0]
	
	for x in ids:
		dirData[int(res[0][ids.index(x)])] = x

	dirDataSorted = {}

	for key in sorted(dirData.iterkeys()):
		dirDataSorted[key] = dirData[key]

	return dirDataSorted

def fetchOldData():
	with open(_LAST_SAVE_FILE, 'rb') as fp:
		data = json.load(fp)
	return data


def saveLast(json_in):

	for j in json_in:
		if 'pafy' in j:
			j['pafy'] = j['pafy'].__str__()

	file_path = '%s/%s_%s' % (_STORE_PATH, datetime.now().strftime(_DT_FORMAT), _SAVE_FILE)
	f = open(file_path, 'wt')
	j = json.dumps(json_in, indent=4)
	print "saving latest metadata..."
	f.write(j)

def repairMissing(dir_data, playlist_data):


	playlist_data_updated = {'playlist_id': playlist_data['playlist_id'], 
							 'description': playlist_data['description'], 
							 'title': playlist_data['title'], 
							 'items':[]}

	items = playlist_data_updated['items']
	newitems = playlist_data['items']
	olddata = fetchOldData()
	olditems = olddata['items']
	old_ids = [i['playlist_meta']['encrypted_id'] for i in olditems]
	new_ids = [i['playlist_meta']['encrypted_id'] for i in newitems]
	dir_ids = dir_data.values()

	def findInDict(encrypted_id):
		return next((i for i in playlist_data['items'] if i['playlist_meta']['encrypted_id'] == encrypted_id), None)

	for x in olditems:
		curr = x['playlist_meta']['encrypted_id']

		if curr in dir_ids and curr in new_ids:
			pl_item = findInDict(curr)
			items.append(pl_item)

		elif curr not in dir_ids and curr not in old_ids:
			pl_item = findInDict(curr)
			items.append(pl_item)

		else: 
			print "adding removed: %s" % (curr) 
			items.append({'removed':'1', 'playlist_meta': {'pafy': 'removed', 'encrypted_id': curr}})

	updated_ids = [i['playlist_meta']['encrypted_id'] for i in items]
	for y in newitems:
		curr = y['playlist_meta']['encrypted_id']

		if curr not in updated_ids:
			items.append(y)

	saveLast(items)
	return add_index(playlist_data_updated)

def dlVideos(playlist_data, modified=False):
	
	if modified == True:
		playlist_data_idxd = playlist_data
	else:
		playlist_data_idxd = getPlaylistData()

	existing_dirs = [x[1] for x in os.walk(_STORE_PATH)][0]

	playlist_data_len = int(len(playlist_data['items']))
	existing_dirs_len = int(len(existing_dirs))
	diff = playlist_data_len - existing_dirs_len

	if diff < 0:
		print "Looks like there are %s vidoes in the playlist" % (diff)
		'''figure out the gaps (which ids are present, which arent), make fixes to data passed around(add dummy entry to data), send back through?'''
		dirData = getDirData()

		playlist_data_idxd = repairMissing(dirData, playlist_data_idxd)

		dlVideos(playlist_data_idxd, modified=True)

	else:
		for i in playlist_data_idxd['items']:
			vid_id = i['playlist_meta']['encrypted_id']
			order_id = i['add_order']
			dirname = vid_id
			filepath = "%s/%s/%s" % (_STORE_PATH, order_id, dirname)
			if str(order_id) not in existing_dirs:
					#TODO - factor gdata in
					title = i['playlist_meta']['title']
					vid_url = _BASE+_VID_PATH+vid_id
					video = pafy.new(vid_url, gdata=True)
					best_dl = video.getbest(preftype="mp4")
					ext = best_dl.extension
					mkdir_p(filepath)
					print "now downloading %s - %s to %s" % (order_id, title, filepath)
					best_dl.download(filepath=filepath)
					print "creating md5 hash..."
					vidname = [e for e in os.listdir(filepath) if e.endswith(ext)]
					videofile = filepath + '/' + vidname[0]
					h = hashlib.md5(open(videofile).read()).hexdigest()
					i['playlist_meta']['md5'] = h
					metadata = json.dumps(i['playlist_meta'], indent=4)
					metadata_file = './videos/%s/%s.json' % (order_id, vid_id)
					j = open(metadata_file, 'wt')
					print "depositing metadata for %s" % (title)
					j.write(metadata)
				

if __name__ == '__main__':
	print "you have started the preserver..."
	data = getPlaylistData()
	dlVideos(data)