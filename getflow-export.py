# coding: utf-8
"""Process a data export from Flow (getflow.com).

Flow data is a zip that extract looks like this:

    index.html
    lists/
        {List}.html
        {Group}/
            List.html

Expects to be given the path to the root directory.

Notes:
   - Does not currently maintain folder structure, folders become flat.
   - Not sure about attachment/images, I don't use them or handle them here.

Limitations:
    - Flow's export does not contain information about recurring tasks.
      If the task was created by the user "Flow", it presumably is
      recurring.
    - It does not contain information about which tasks are flagged.

"""

import re
import sys
import os
import datetime
from time import mktime
from os.path import join, exists
import json
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
import html2text


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


def activity_log(log, match):
    """Find an entry in the activity log."""
    for entry in log:
        if match in entry['summary']:
            return entry['date']
    return None


def text(el):
    """Text of an element, or None."""
    if not el:
        return None
    return el.text.strip()


def stderr(msg, *args):
    msg = msg % tuple(args)
    print >> sys.stderr, msg.encode(sys.stderr.encoding)


def process_one_list_file(filename):
    stderr(u'Processing %s', filename)
    with open(filename, 'r') as f:
        soup = BeautifulSoup(f.read())

    list_name = soup.title(text=True)[0]
    task_elems = soup.find_all("li", class_="task")
    stderr(u'Found list {0} with {1} tasks'.format(list_name, len(task_elems)))

    tasks = []
    for el in task_elems:
        task = {
            'title': list(el.find('a', class_='body').children)[0].strip(),
            'completed': 'completed' in el.find('a', class_='body')['class'],
            'assigned-to': detail(el, 'Assigned to'),
            # 'created-on': detail(el, 'Created on', dateparser.parse),
            # 'completed-on': detail(el, 'Completed on', dateparser.parse, True),
            'subscribers': detail(el, 'Subscribers'),


            'activities': [],
            #'due-on': None,
            #'subtasks': []
        }
        tasks.append(task)

        if el.find('span', class_="due-on"):
            task['due-on'] = dateparser.parse(el.find('span', class_="due-on").text.strip(u'— '))
        #
        for subtask in el.findAll('li', class_='subtask'):
            task.setdefault('subtasks', []).append(subtask.text.strip())

        for activity_el in el.findAll('li', class_='activity'):
            activity = {
                'summary': activity_el.find(class_='summary').text.strip(),
                'date': dateparser.parse(activity_el.find(class_='date').text.strip())
            }

            detail_el = activity_el.find(class_='activity-detail')
            if detail_el:
                detail_html = "".join([str(x) for x in detail_el.contents])
                detail_html = detail_html.decode('utf-8')
                activity['detail'] = detail_html
                activity['detail_plain'] = html2text.html2text(detail_html)

            if detail_el and 'comment' in detail_el['class']:
                activity['is_comment'] = True
            task['activities'].append(activity)

        task['created-at'] = \
            activity_log(task['activities'], 'created this task in')

    return (list_name, tasks)


def main(prog, argv):
    if len(argv) != 1:
        print >> sys.stderr, 'Usage: {0} EXTRACTED_EXPORT_ZIP_DIR'.format(prog)
        return
    p = argv[0]

    if not exists(join(p, 'lists')):
        print >> sys.stderr, "No lists/ folder, I need the path where index.html is located."
        return

    lists = {}
    for dirpath, dirnames, filenames in os.walk(join(p, 'lists/')):
        html_files = set(filter(lambda f: f.endswith('.html'), filenames))

        # filenames should be 343434-List-page-X.html
        # We want to process all pages in a group
        while html_files:
            first_file = list(sorted(list(html_files)))[0]
            basename = re.match(r'^(.*?)-page-\d+.html', first_file).groups()
            # Now get all page files for this group
            all_page_files = filter(lambda f: f.startswith('%s-page-' % basename), html_files)
            all_page_files.sort()

            list_name = None
            tasks = []
            for filename in all_page_files:
                page_name, page_tasks = process_one_list_file(join(dirpath, filename))

                if list_name:
                    assert page_name == list_name
                else:
                    list_name = page_name

                tasks.extend(page_tasks)

            # Add tasks from all pages to global result
            # Make sure list name is unique
            final_name = list_name
            i = 0
            while list_name in lists:
                final_name = '%s (%s)' % (list_name, i)
                i += 1
            lists[final_name] = tasks

            # Remove the processed files from global list of files
            html_files -= set(all_page_files)


    class DateEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, datetime.datetime):
                #return int(mktime(obj.timetuple()))
                return obj.isoformat()
            return json.JSONEncoder.default(self, obj)
    print json.dumps(lists, cls=DateEncoder, indent=4)


if __name__ == '__main__':
    main(sys.argv[0], sys.argv[1:])