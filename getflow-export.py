"""Process a data export from Flow (getflow.com).

Flow data is a zip that extract looks like this:

    index.html
    lists/
        {List}.html
        {Group}/
            List.html

Expects to be given the path to the root directory.
"""

import sys
import os
import datetime
from time import mktime
from os.path import join, exists
import json
from bs4 import BeautifulSoup
from dateutil import parser as dateparser


def detail(task_el, name, transform=None, optional=False):
    """Get the detail "name" from the task element."""
    for item in task_el.find(class_='task-info').findAll('li'):
        #print filter(bool, ([
        #    (s if isinstance(s, basestring) else s.text).strip(' :\n\r\t')
        #    for s in item.children]))
        title, value = filter(bool, ([
            (s if isinstance(s, basestring) else s.text).strip(' :\n\r\t')
            for s in item.children]))

        if title.strip().lower() == name.lower():
            if transform and value:
                value = transform(value)
            return value
    if optional:
        return None
    raise ValueError('detail %s not found for %s' % (name, task_el))


def text(el):
    """Text of an element, or None."""
    if not el:
        return None
    return el.text.strip()


def process_folder(filename):
    print >> sys.stderr, 'Processing %s' % filename
    with open(filename, 'r') as f:
        soup = BeautifulSoup(f.read())

    list_name = soup.title(text=True)[0]
    task_elems = soup.find_all("li", class_="task")
    print >> sys.stderr, 'Found list {0} with {1} tasks'.format(list_name, len(task_elems))

    tasks = []
    for el in task_elems:
        task = {
            'title': list(el.find('a', class_='body').children)[0].strip(),
            'completed': 'completed' in el['class'],
            'created-by': detail(el, 'Created by'),
            'assigned-to': detail(el, 'Assigned to'),
            'created-on': detail(el, 'Created on', dateparser.parse),
            'completed-on': detail(el, 'Completed on', dateparser.parse, True),
            'followers': detail(el, 'Followers'),
            'activities': []
        }
        tasks.append(task)
        #completed_at = ac.find(class_='completed-at'.text.strip())
        #if completed_at:
        #    task['completed_at'] = dateparser.parse(completed_at)

        for activity_el in el.findAll('li', class_='activity'):
            task['activities'].append({
                'summary': activity_el.find(class_='summary').text.strip(),
                'detail': text(activity_el.find(class_='activity-detail')),
                'date': activity_el.find(class_='date').text.strip()
            })

    return (list_name, tasks)


def main(prog, argv):
    if len(argv) != 1:
        print >> sys.stderr, 'Usage: {0} EXTRACTED_EXPORT_ZIP_DIR'.format(prog)
        return
    p = argv[0]

    if not exists(join(p, 'lists')):
        print >> sys.stderr, "No lists/ folder, I need the path where index.html is located."

    lists = {}
    for dirpath, dirnames, filenames in os.walk(join(p, 'lists/')):
        for filename in filter(lambda f: f.endswith('.html'), filenames):
            list, tasks = process_folder(join(dirpath, filename))

            list_name = list
            i = 0
            while list_name in lists:
                list_name = '%s (%s)'.format(list, i)
                i += 1
            lists[list_name] = tasks


    class DateEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, datetime.datetime):
                return int(mktime(obj.timetuple()))
            return json.JSONEncoder.default(self, obj)
    print json.dumps(lists, cls=DateEncoder, indent=4)


if __name__ == '__main__':
    main(sys.argv[0], sys.argv[1:])