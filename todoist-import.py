"""Convert fromt the GetFlow export json to Todoist.
"""

import sys
import json
import todoist
import html2text
import time


def main(prog, argv):
    if len(argv) != 2:
        print >> sys.stderr, 'Usage: {0} GETFLOW_JSON API_TOKEN'.format(prog)
        return
    datafile = argv[0]
    token = argv[1]

    with open(datafile, 'r') as f:
    	data = json.loads(f.read())


    api = todoist.TodoistAPI(token)

    for listname, tasks in data.iteritems():
    	print 'Adding project %s with %s items' % (listname, len(tasks))

    	project = api.projects.add(listname)

    	count_added = 0
    	for task in tasks:
    		if task['completed']:
    			# Skip all completed tasks
    			continue

    		# #
    		# if not task.get('due-on'):
    		# 	continue

    		# The item itself
    		if task.get('due-on'):
    			task['due-on'] = task['due-on'].replace('T00:00:00', '')
    		item = api.items.add(task['title'], project['id'], date_string=task.get('due-on'))

    		# Subtasks
    		for subtask in task.get('subtasks', []):
    			subtitem = api.items.add(subtask, project['id'], indent=2)

    		# Add one comment indicating the time - only to those that have notes
    		has_notes = any([a for a in task.get('activities', []) if a.get('is_comment', False)])
    		if has_notes and task['created-at']:
    			note = api.notes.add(item['id'], 'Added in Flow at %s' % task['created-at'])

    		# Comments
    		for activity in task.get('activities', []):
    			if not activity.get('is_comment', False):
    				continue
    			note = api.notes.add(item['id'], html2text.html2text(activity['detail']))
    			notes_added = True

    		count_added += 1

    		# Todoist only allows 100 queued commands, so commit each
    		# todo individually to be sure.
    		result = api.commit()
	    	print result
	    	if 'error_code' in result:
	    		raise ValueError('error')

    		# Too many requests reached, it says
	    	import time
	    	time.sleep(0.1)


    	print "   Commiting project add with %d tasks" % count_added
    	result = api.commit()
    	print result
    	if result and 'error_code' in result:
    		raise ValueError('error')

    	# Too many requests reached, it says
    	import time
    	time.sleep(1)



if __name__ == '__main__':
    main(sys.argv[0], sys.argv[1:])