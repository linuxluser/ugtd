#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

"""ncurses Python application for "Getting Things Done".


[Methodology - Getting Things Done]


[Method - Todo.txt]
Todo.txt is a text data format designed to store personal task data. It follows
philosophies of simplicity, portability and functionality.

More details here:

    http://todotxt.com/


Todo.txt is intending to follow the GTD methodology. It does do this but it
also, by necessity, imposes a specifc approach to the GTD methodology. This is
why I see it as a "method" more than just a format.

The creators do a fairly good job of explaining this method here:

    https://github.com/ginatrapani/todo.txt-cli/wiki/The-Todo.txt-Format


Salient point about this method are:
 - Meta-data about tasks only includes dates, completion, priority, projects and
   contexts.
 - There is no nesting of priority, projects or contexts. Your tasks are "flat".
 - Dates to do not include time.
 - Priorities are letters only, not numbers.
 - All meta data can be written right into your task description.


[TaskWarrior - What It Got Wrong]
TaskWarrior is a command-line tool for implementing personal task management and
is probably the most popular one. TaskWarrior has good documentation and can be
used to facilitate a GTD methodology. It has a proven track-record of being very
useful and facilating productivity among those of us who still use the terminal.

Besides inventing it's own serialization format (they could have just use JSON,
no?), I found a few things frustrating about it to the point where I stopped
using it altogether. I thought and though about my experience with TaskWarrior
and the many other task management apps I tried out. I really wanted something
that I could use on a powerful UNIX shell but something about TaskWarrior just
didn't make it work right for me. Then I realized what it was: context.

No, not "context" in the todo.txt sense (mentioned above). Context, as in, what
is happening in my head as I work through my task list. It's the thing that GUI
applications have that terminal applications can't have. With a GUI app, I can
instantly and visually see all of my tasks. I can then pluck out ones I need to
change (mark "done"!) and move on. All the GUI apps focussed on the right
thing: presenting the tasks and allowing me to take my sweet time to decide what
to do. TaskWarrior could not do this. It presented the data, then would exit.
Once I figured out what to do, I told TaskWarrior through lots of typing and
then it happened. But I sacrificed context. I had to reprint the list again to
decide on the next thing to do.

By the time I had done my morning routine, my fingers were tired and I had a
feeling of not quite remembering what changes I had done. The problem was that
I could perform an action or get context (print tasks) but not both. Every time
I got context, I had to lose it to do something and then go back and get it
again.

Another problem was all the typing. If you look at your command history, you'll
see a lot of the same patterns over and over again with very few things changed.
This is an indicator that the user is being asked to do a lot of overhead to do
something simple.

"But that's what you do on a terminal!" Yes, but not if you have to do the same
thing over and over again. The terminal is a user interface and every terminal
application needs to strive to be as user-friendly as possible. If you're
making a website or a GUI app, you focus on how users go through the app and
use the essential functions of it. You care and you modify the design to appeal
to more users and make things easy without sacrificing functionality. Why should
a terminal application not do the same?


So TaskWarrior sucks at presenting a persistent context from which I can make
multiple decisions on. And TaskWarrior makes me type a lot of stuff for it.
Those two things made it a very user-unfriendly application for me. As a result,
I had to stop using it, no matter how many features it had.


[Application - Task Menu]
Like any good programmer (is that what I am?) I decided to write something that
took a different approach, in hopes that it would be useful to me and possibly
others.

Task Menu, is a curses-based application. This gives it the contextual power of
the GUI apps but the portability and leaness of a terminal app. It's the best
of both worlds!

Task Menu also applies a limited set of "views" you can have on your tasks. It
removed the ability for you, the user, to add new views or customize in that
way. This is another deviation from TaskWarrior which boasts customization.

I believe that by making the app ncurses-based and by having pre-defined views,
you, the user, can use your brain for what it's supposed to be used for: task
management.

There are generally 2 "modes" that your brain is in right before you fire up
your personal task management system: 1) you don't remember what needed to be
done and you need to see it OR 2) you have something very specific in mind that
you need to do and just want to do it.

For scenario #1, you need a way to see lots of tasks at once and scroll through
them if needed. curses works for this.

For scenario #2, you need to type as little as possible to tell the application
what to do. curses again words great because your enviornment (your context) is
already there, so all you need to do is hit a single key and something can
happen ("done"!).


[So why the limited number of views?]
Given the Todo.txt method, with it's "3 axis" of tasks, it turns out that we can
pivot off of those axis in 6 possible ways (3 factorial, for you math nerds).
They are:

   - By Priority then Project
   - By Priority then Context
   - By Project  then Priority
   - By Project  then Context
   - By Context  then Priority
   - By Context  then Project

You pivot off of one of then first, that leaves only 2 more "axis" to pivot
from. So you pivot off of the second one, and that leaves you with the last
remaining "axis" automatically. From those two pivot points, the application
can know everything it needs to present to you a filtered view of the tasks
that match that criteria.

And THAT is how Task Menu works. Since each tasks contains all its meta-data
already, all you need to see is the task itself. Thus, the only possible
variations you could have come from the "axis" themselves.


I don't know if Todo.txt intended this as a consequence. But the data itself
makes this possible.

"""

import collections
import datetime
import inspect
import itertools
import os
import string
import sys
import time

import urwid


#TODO_TEXT_FILE = os.path.join(os.path.expanduser('~'), '.todo.txt')
TODO_TEXT_FILE = os.path.join(os.path.expanduser('~'), 'todo.test.txt')

DIMENSIONS = ('projects', 'contexts', 'priority')

#            LABEL   -  CATEGORY  -  GROUPING
VIEWS = ((u'[Pri/Ctx]', 'priority', 'contexts'),
         (u'[Prj/Ctx]', 'projects', 'contexts'),
         (u'[Prj/Pri]', 'projects', 'priority'),
         (u'[Ctx/Prj]', 'contexts', 'projects'),
         (u'[Ctx/Pri]', 'contexts', 'priority'),
         (u'[Pri/Prj]', 'priority', 'projects'))


class Border(urwid.LineBox):
  """Draws a border around the widget with optional title.

  Same as urwid.LineBox but the title is a little fancier and it's aligned left.
  """

  def __init__(self, *args, **kwargs):
    super(Border, self).__init__(*args, **kwargs)

    # Remove the first line in the title to force the title to align left
    if len(self.tline_widget.contents) == 3:
      self.tline_widget.contents.pop(0)

  def format_title(self, text):
    if not text:
      return ''
    return u'┤ %s ├' % text


class Task(urwid.WidgetPlaceholder):

  def __init__(self, S, todotxtfile):
    self._todotxtfile = todotxtfile
    self.UpdateFromString(S)
    super(Task, self).__init__(self.text_widget_attrmap)

  def __str__(self):
    return self.text

  def __repr__(self):
    return '%s(%r)' % (self.__class__.__name__, self.text)

  def selectable(self):
    return True
  
  def keypress(self, size, key):
    return key

  def _BuildTextWidget(self):
    if self.completed:
      icon = 'x'
    elif self.creation_date and (datetime.date.today() - self.creation_date).days > 21:
      icon = '!'
    else:
      icon = ' '
    self.text_widget = urwid.Text([('prefix', '  '),
                                   '[%s]' % icon,
                                   ' ',
                                   self.text])
    self.text_widget_attrmap = urwid.AttrMap(self.text_widget,
                                     {'prefix': 'prefix:normal', None: 'normal'},
                                     {'prefix': 'prefix:selected', None: 'selected'})
    return self.text_widget_attrmap

  def _Parse(self, line):
    """Parse a single-line string S as a task in the todo.txt format.

    See: https://github.com/ginatrapani/todo.txt-cli/wiki/The-Todo.txt-Format
    """
    line_stripped = line.strip()
    
    # Completed
    if line_stripped.startswith('x '):
      completed = True
      line_stripped = line_stripped[2:]
    else:
      completed = False

    # Convenience string splitting function without the traceback mess
    def head_tail(s, split_on=None):
      if s:
        try:
          h,t = s.split(split_on, 1)
        except ValueError:
          h = s
          t = ''
        return h,t
      else:
        return '', ''

    # Completion date
    completion_date = None
    if completed:
      word, tail = head_tail(line_stripped)
      try:
        time_struct = time.strptime(word, '%Y-%m-%d')
      except ValueError:
        pass
      else:
        completion_date = datetime.date(*time_struct[:3])
        line_stripped = tail

    # Priority
    if line_stripped.startswith('('):
      end_pri = line_stripped.find(') ')
      if end_pri != -1:
        pri = line_stripped[1:end_pri].strip()
        if len(pri) == 1 and pri in string.uppercase:
          priority = pri
        else:
          priority = None
        line_stripped = line_stripped[end_pri+1:].strip()
      else:
        priority = None
    else:
      priority = None

    # Creation date
    creation_date = None
    word, tail = head_tail(line_stripped)
    try:
      time_struct = time.strptime(word, '%Y-%m-%d')
    except ValueError:
      pass
    else:
      creation_date = datetime.date(*time_struct[:3])
      line_stripped = tail

    # Body - main part of text after priority/dates but with contexts/projects in-tact
    body = line_stripped

    # Contexts and projects
    contexts = []
    projects = []
    for word in line_stripped.split():
      if word.startswith('+'):
        prj = word[1:]
        if prj:
          projects.append(prj)
      elif word.startswith('@'):
        ctx = word[1:]
        if ctx:
          contexts.append(ctx)

    return {'text':            line,
            'body':            body,
            'priority':        priority,
            'creation_date':   creation_date,
            'completion_date': completion_date,
            'completed':       completed,
            'contexts':        contexts,
            'projects':        projects,
           }

  def UpdateFromString(self, S):
    """Update this Task instance with a new task string S."""
    # In cases of empty string we assign empty results
    if not S:
      self.text            = ''
      self.completed       = False
      self.completion_date = None
      self.creation_date   = None
      self.priority        = None
      self.body            = ''
      self.projects        = []
      self.contexts        = []

    else:
      # Skim off the top line if given a multi-line string
      self.text = S.splitlines()[0]

      # Parse
      values = self._Parse(self.text)

      # Assign attributes
      self.completed       = values['completed']
      self.completion_date = values['completion_date']
      self.creation_date   = values['creation_date']
      self.priority        = values['priority']
      self.body            = values['body']
      self.projects        = values['projects']
      self.contexts        = values['contexts']

    # Update the widget
    self.original_widget = self._BuildTextWidget()


class Keyword(urwid.WidgetPlaceholder):

  def __init__(self, S):
    self.text_widget = urwid.Text(S)
    widget = urwid.AttrMap(self.text_widget, 'normal', 'selected')
    super(Keyword, self).__init__(widget)

  @property
  def text(self):
    return self.text_widget.text

  def selectable(self):
    return True
  
  def keypress(self, size, key):
    return key


class TaskEdit(urwid.Edit):
  """Custom Edit widget which provides convenient keypress mappings for editing."""

  def __init__(self, task):
    self.clipboard = ''
    caption = task.text_widget.text[:6]
    edit_text = task.text_widget.text[6:]
    super(TaskEdit, self).__init__(('editbox:caption', caption), edit_text)

  def keypress(self, size, key):
    # Cut word left of cursor
    if key in ('ctrl w', 'ctrl backspace'):
      # Split at cursor, preserving character under it
      text = self.edit_text
      pos = self.edit_pos
      left, right = text[:pos], text[pos:]

      # Find the last word in 'left' and remove it
      head_tail = left.rsplit(None, 1)
      if not head_tail:
        last_word_index = 0   # Nothing but whitespace, so save nothing
      else:
        if len(head_tail) == 1:
          last_word = head_tail[0]
        else:
          last_word = head_tail[1]
        last_word_index = left.rfind(last_word)
      self.clipboard = left[last_word_index:]
      left = left[:last_word_index]

      # Set text and position
      self.set_edit_text(left + right)
      self.set_edit_pos(last_word_index)

    # Cut all text left of cursor
    elif key == 'ctrl u':
      text = self.edit_text
      pos = self.edit_pos
      left, right = text[:pos], text[pos:]
      self.set_edit_text(right)
      self.set_edit_pos(0)
      self.clipboard = left

    # Cut all text right of the cursor
    elif key == 'ctrl k':
      text = self.edit_text
      pos = self.edit_pos
      left, right = text[:pos], text[pos:]
      self.set_edit_text(left)
      self.set_edit_pos(len(left))
      self.clipboard = right

    # Move position to the start of the line
    elif key == 'ctrl a':
      self.set_edit_pos(0)

    # Move position to the end of the line
    elif key == 'ctrl e':
      self.set_edit_pos(len(self.edit_text))

    # Move one position forward
    elif key == 'ctrl f':
      self.set_edit_pos(self.edit_pos + 1)

    # Move one position backwards
    elif key == 'ctrl b':
      self.set_edit_pos(self.edit_pos - 1)

    # Change priority
    elif key in ('+', 'up', '-', 'down'):
      text = self.edit_text
      if not text.startswith('x '):
        pos = self.edit_pos
        pri = text[:4]
        if pri[0] == '(' and pri[2] == ')' and pri[3] == ' ':
          priority = pri[1].upper()
        else:
          priority = None

        # Decrease priority
        if key in ('+', 'up'):
          if priority is None:
            self.set_edit_text('(A) %s' % text)
            self.set_edit_pos(pos + 4)
          elif priority != 'Z':
            priority = chr(ord(pri[1].upper()) + 1)
            self.set_edit_text('(%s) %s' % (priority, text[4:]))

        # Increase priority
        if key in ('-', 'down'):
          if priority:
            if priority == 'A':
              self.set_edit_text(text[4:])
              self.set_edit_pos(pos - 4)
            else:
              priority = chr(ord(pri[1].upper()) - 1)
              self.set_edit_text('(%s) %s' % (priority, text[4:]))

    else:
      return super(TaskEdit, self).keypress(size, key)


class VimNavigationListBox(urwid.ListBox):
  """ListBox that also accepts vim navigation keys."""

  VIM_KEYS = {
      'k'     : 'up',
      'j'     : 'down',
      'ctrl u': 'page up',
      'ctrl b': 'page up',
      'ctrl d': 'page down',
      'ctrl f': 'page down',
      'h'     : 'left',
      'l'     : 'right',
  }

  def __init__(self, items, panel):
    self.items = items
    self._panel = panel
    self.edit_mode = False
    super(VimNavigationListBox, self).__init__(items)

  def keypress(self, size, key):
    if self.edit_mode:
      # Ignore page up/down in edit mode
      if key in ('page up', 'page down'):
        return

    # Vim navigation translation
    else:
      if self.VIM_KEYS.has_key(key):
        key = self.VIM_KEYS[key]

    return super(VimNavigationListBox, self).keypress(size, key)


class TaskPile(urwid.Pile):
  """An urwid.Pile that handles groups of Tasks and editing them."""

  def __init__(self, tasks, group, tasklistbox):
    self.group = group
    self.tasks = tasks
    self.tasklistbox = tasklistbox
    self.items = [urwid.Text(group)]
    self.items.extend(tasks)
    self.items.append(urwid.Divider())
    super(TaskPile, self).__init__(self.items)

    # Start out in 'nav' mode
    self._mode = 'nav'

  def keypress(self, size, key):
    ###################
    ### NAV MODE
    if self._mode == 'nav':
      # Enter 'edit' mode
      if key == 'enter' and isinstance(self.focus, Task):
        self._preserved_task = self.focus
        edit_widget = self._BuildEditWidget(self._preserved_task)
        self.contents[self.focus_position] = (edit_widget, ('pack', None))
        self._mode = 'edit'
        self.tasklistbox.edit_mode = True

      return super(TaskPile, self).keypress(size, key)

    ###################
    ### EDIT MODE
    elif self._mode == 'edit':

      # Exit edit mode
      if key in ('enter', 'esc'):
        # Submit changes if any
        if key == 'enter':
          edit_widget = self.focus.original_widget
          if self._preserved_task.text != edit_widget.get_edit_text():
            # Get before/after properties and update the task itself
            old_properties = self._preserved_task.__dict__.copy()
            self._preserved_task.UpdateFromString(edit_widget.get_edit_text())
            new_properties = self._preserved_task.__dict__.copy()
            # Start a chain reaction so all widgets can deal with the changes
            self.tasklistbox.DoTaskChangeWork(old_properties, new_properties)

        self.contents[self.focus_position] = (self._preserved_task, ('pack', None))
        self._preserved_task = None
        self.tasklistbox.edit_mode = False
        self._mode = 'nav'
        return

      return super(TaskPile, self).keypress(size, key)

  def _BuildEditWidget(self, task):
    widget = TaskEdit(task)
    widget = urwid.AttrMap(widget, 'editbox', 'editbox')
    return widget


class TaskListBox(VimNavigationListBox):
  """
  """

  def __init__(self, piles, taskpanel, category, keyword, grouping):
    # 'items' -> 'tasks'
    # new 'piles'
    self.piles = piles
    self.taskpanel = taskpanel
    self.category = category
    self.keyword = keyword
    self.grouping = grouping
    self._mode = 'nav'
    super(TaskListBox, self).__init__(piles, taskpanel)

  def _BuildEditWidget(self, task):
    widget = TaskEdit(task)
    widget = urwid.AttrMap(widget, 'editbox', 'editbox')
    return widget

  def DoTaskChangeWork(self, old_properties, new_properties):
    ########################
    ### Added task
    if not old_properties:
      groups_added_to = new_properties[self.grouping]
      if not hasattr(groups_added_to, '__iter__'):
        groups_added_to = [groups_added_to]
      groups_removed_from = []

    ########################
    ### Deleted task
    elif not new_properties:
      groups_removed_from = old_properties[self.grouping]
      if not hasattr(groups_removed_from, '__iter__'):
        groups_removed_from = [groups_removed_from]
      groups_added_to = []

    ########################
    ### Modified task
    else:
      old_group = old_properties[self.grouping]
      new_group = new_properties[self.grouping]
      if hasattr(old_group, '__iter__'):
        groups_removed_from = set(old_group) - set(new_group)
        groups_removed_from = sorted(groups_removed_from)
        groups_added_to = set(new_group) - set(old_group)
        groups_added_to = sorted(groups_added_to)
      else:
        if old_group != new_group:
          groups_removed_from = [old_group]
          groups_added_to = [new_group]
        else:
          groups_removed_from = []
          groups_added_to = []


class KeywordPanel(urwid.WidgetPlaceholder):
  """Panel to hold the keywords and allow selection of tasks.

  """

  def __init__(self, app, keywords_dict={}):
    self.app = app
    self._keywords_dict = keywords_dict
    self._listboxes = {}
    for cat,keywords in self._keywords_dict.items():
      kw_widgets = [Keyword(k or u'--none--') for k in keywords]
      listbox = VimNavigationListBox(kw_widgets, self)
      self._keywords_dict[cat] = kw_widgets
      self._listboxes[cat] = listbox
    self._selected_category = self._keywords_dict.keys()[0]
    self.padding_widget = urwid.Padding(urwid.SolidFill(u'x'), left=1, right=1)
    self.border_widget = Border(self.padding_widget, 'Empty')
    super(KeywordPanel, self).__init__(self.border_widget)

  def render(self, size, focus=False):
    """Intercept render() in case it's because the selected keyword changed.
    """
    self.app.startKeywordChange(self.GetSelectedKeyword(), None)
    return super(KeywordPanel, self).render(size, focus)

  def GetKeywords(self, category):
    keywords = []
    for w in self._listboxes[category].body.contents:
      text = w.text_widget.text
      if text == '--none--':
        keywords.append(None)
      else:
        keywords.append(text)
    return keywords

  def GetSelectedKeyword(self):
    """Get the keyword that is selected and in the current view."""
    text = self._listboxes[self._selected_category].focus.text
    if text == '--none--':
      return None
    else:
      return text

  def doViewChange(self, new_view, old_view):
    new_category,_ = new_view
    if new_category in self._listboxes:
      listbox = self._listboxes[new_category]
      self.padding_widget.original_widget = listbox
      self.border_widget.set_title(new_category.capitalize())
      self._selected_category = new_category

  def doKeywordChange(self, new_keyword, old_keyword):
    return


class TaskPanel(urwid.WidgetPlaceholder):

  def __init__(self, app, tasks):
    self.app = app
    self.tasks = tasks
    self._listboxes = {}

    # We only want to deal with tasks that are incomplete or recently completed
    tasks = []
    for task in self.tasks:
      if task.completed:
        if task.completion_date:
          if (datetime.date.today() - task.completion_date).days < 2:
            tasks.append(task)
      else:
        tasks.append(task)

    # Build ListBoxes for every permutation of (category, keyword, grouping)
    permutations = itertools.permutations(DIMENSIONS)
    for category, grouping, sorting in permutations:
      for keyword in self.app.keyword_panel.GetKeywords(category):
        # Find matching Tasks
        matching_tasks = []
        for task in tasks:
          that_keyword = getattr(task, category)
          if hasattr(that_keyword, '__iter__') and keyword in that_keyword:
            matching_tasks.append(task)
          elif that_keyword == keyword:
            matching_tasks.append(task)
        # Group matching Tasks
        groups = collections.defaultdict(list)
        for task in matching_tasks:
          group_value = getattr(task, grouping)
          if hasattr(group_value, '__iter__'):
            if len(group_value) == 0:
              groups[None].append(task)
            else:
              [groups[g].append(task) for g in group_value]
          else:
            groups[group_value].append(task)
        # Sort tasks in each group by 'sorting'
        for group_tasks in groups.values():
          group_tasks.sort(key=lambda t: getattr(t, sorting))

        # Create a ListBox from groups
        piles = []
        for group in sorted(groups):
          if group is None:
            group_label = u'--none--'
          else:
            group_label = unicode(group)
          pile = TaskPile(groups[group], group_label, None)
          piles.append(pile)

        # Add listbox to our set of ListBoxes
        key = (category, keyword, grouping)
        listbox = TaskListBox(piles, self, category, keyword, grouping)
        self._listboxes[key] = listbox

        # Ensure all piles have a reference to the listbox
        for pile in piles:
          pile.tasklistbox = listbox 

    # Create decorative widgets and initialize ourselves
    self.padding_widget = urwid.Padding(urwid.SolidFill(u'x'), left=1, right=1)
    self.border_widget = Border(self.padding_widget, 'Empty')
    super(TaskPanel, self).__init__(self.border_widget)

    self.category = ''
    self.grouping = ''
    self.sorting = ''

  def _SetTitle(self):
    title = 'Tasks by %s' % self.grouping.capitalize()
    self.border_widget.set_title(title)

  def DoTaskChangeWork(self, old_properties, new_properties):
    ########################
    ### Added task
    if not old_properties:
      return

    ########################
    ### Deleted task
    elif not new_properties:
      return

    ########################
    ### Modified task
    else:
      for listbox in self._listboxes.values():
        listbox.DoTaskChangeWork(old_properties, new_properties)

  def doViewChange(self, new_view, old_view):
    category, grouping = new_view
    keyword = self.app.keyword_panel.GetSelectedKeyword()

    listbox = self._listboxes[(category, keyword, grouping)]
    self.padding_widget.original_widget = listbox

    # We sort by whatever is not the category or grouping dimension
    sorting = set(DIMENSIONS).difference((category, grouping)).pop()

    self.category = category
    self.grouping = grouping
    self.sorting = sorting

    self._SetTitle()

  def doKeywordChange(self, new_keyword, old_keyword):
    listbox = self._listboxes[(self.category, new_keyword, self.grouping)]
    self.padding_widget.original_widget = listbox
    self._SetTitle()


class ViewPanel(Border):
  """Top panel with selectable 'views' on Task data.

  The ViewPanel has a reference to the TaskPanel so that when the view is
  changed, that event can be passed on to the TaskPanel to react to it.
  """

  def __init__(self, app):
    self.app = app

    # Create urwid.Text widgets and save them in a mapping
    text_widgets = {}
    for label, category, grouping in VIEWS:
      view = (category, grouping)
      text_widgets[view] = urwid.Text(('normal', label))
    self.text_widgets = text_widgets

    # Place urwid.Text widgets in the UI
    widget = urwid.Columns([(11, text_widgets[V[1:]]) for V in VIEWS])
    widget = urwid.Padding(widget, left=1)
    super(ViewPanel, self).__init__(widget)

    # Select first view
    # FIXME: this is already done in Application.__init__ no?
    self.selected_view = VIEWS[1][1:]
    self.doViewChange(VIEWS[0][1:], None)

  def doViewChange(self, new_view, old_view):
    """Select a new view."""
    if new_view == self.selected_view:
      return

    old_widget = self.text_widgets[self.selected_view]
    new_widget = self.text_widgets[new_view]
    old_widget.set_text(('normal', old_widget.text))
    new_widget.set_text(('selected', new_widget.text))
    self.selected_view = new_view

  def doKeywordChange(self, new_keyword, old_keyword):
    return


class TodoTxtFile(object):
  """Manages I/O for a todo.txt file.
  """

  def __init__(self, filename):
    self.filename = filename
    self._lines = open(filename).read().splitlines()
    self.tasks = []

    # Create Tasks and insert them into our file representation, self._lines
    # For empty lines or lines with only spaces, we ignore them. But for lines
    #   with content, we create a Task and keep that task's place in the file
    #   by puting it right back into our self._lines where we found it.
    for i, line in enumerate(self._lines):
      if line and not line.isspace():
        task = Task(line, self)
        self._lines[i] = task  # replace text with a Task object
        self.tasks.append(task)

  def _RewriteFile(self):
    """Rewrite entire file, including any updated content.
    """
    with open(self.filename, 'w') as f:
      for line in self._lines:
        f.write('%s\n' % line)

  def RewriteTaskInFile(self, task, new_text):
    self._RewriteFile()

  def DeleteTaskFromFile(self, task):
    index = self._lines.index(task)
    self._lines.remove(task)
    self._lines.insert(index, '')
    self.tasks.remove(task)
    self._RewriteFile()

  def AppendTaskToFile(self, task):
    with open(self.filename, 'a') as f:
      f.write('%s\n' % task)


class Application(object):
  """Main application to handle run state and event propagation.

  [Events]
  Since this is quite a modest-sized program, I don't want to introduce a
  message-passing framework or include a more robust/feature-rich one as a
  dependency. However, the job still needs to get done for a few basic things
  and the best way to handle that is for widgets "lower down" to tell the
  application about the event and the application then alerts everyone else by
  calling special functions. This is nothing fancy (nor should it be) and it is
  not even async in any way. It's just dumb message passing.

  Initially I did this by having widgets reference other widget if they needed
  to communicate in any way. However, most widgets ended up needing a reference
  to at least some other widget and I writing special code for each pair. This
  got hard to keep up. So I went all the way up the chain and decided to start
  over again with a fresh design pattern and some "standard" function calls. If
  an event happens that something else needs to know about, it only tells the
  application and the application can then run through and tell everybody else.
  Those to whome it does not concern will ignore it. The others will do
  something about it.


  [Application Layout]
  The application has a static top bar, the ViewPanel, from which a particular
  view of the tasks can be chosen. Once a view is known, a set of keywords is
  created in the KeywordPanel, which is always on the left of the screen. These
  keywords determine what set of tasks get put in the TaskPanel. The TaskPanel
  has a subset of the tasks, grouped by either their project, context or priority.


      +----------------------------------------------+
      |                  ViewPanel                   |
      +---------+------------------------------------+
      |         |                                    |
      |         |                                    |
      | Keyword |             TaskPanel              |
      |  Panel  |                                    |
      |         |                                    |
      |         |                                    |
      |         |                                    |
      +---------+------------------------------------+

  """

  PALETTE = [('normal',          '',            ''),
             ('selected',        '',            'dark blue'),
             ('prefix:normal',   'black',       ''),
             ('prefix:selected', '',            'dark red'),
             ('editbox',         'light green,standout', ''),
             ('editbox:caption', '',            'dark red')]

  def __init__(self, tasks):
    # Create widgets
    keywords =  {'projects': sorted(set(p for t in tasks for p in t.projects)),
                 'contexts': sorted(set(c for t in tasks for c in t.contexts)),
                 'priority': sorted(set(t.priority for t in tasks))}
    self.keyword_panel = KeywordPanel(self, keywords)
    self.task_panel = TaskPanel(self, tasks)
    self.view_panel = ViewPanel(self)
    columns = urwid.Columns([(30, self.keyword_panel), self.task_panel], focus_column=0)
    self.browser = urwid.Frame(columns, header=self.view_panel)

    self.startViewChange(VIEWS[0][1:], None)

  def _UnhandledInput(self, key):
    # Exit program
    if key == 'esc':
      raise urwid.ExitMainLoop()

    # Select view
    elif key.isdigit():
      index = int(key)
      if index > 0 and index <= len(VIEWS):
        new_view = VIEWS[index -1][1:]
        old_view = self.view_panel.selected_view
        self.startViewChange(new_view, old_view)

  def Run(self):
    self.main_loop = urwid.MainLoop(self.browser,
                                    palette=Application.PALETTE,
                                    unhandled_input=self._UnhandledInput)
    self.main_loop.run()

  def startViewChange(self, new_view, old_view):
    """Master doViewChange function which calls the others."""
    self.view_panel.doViewChange(new_view, old_view)
    self.keyword_panel.doViewChange(new_view, old_view)
    self.task_panel.doViewChange(new_view, old_view)

  def startKeywordChange(self, new_keyword, old_keyword):
    """Master doKeywordChange function which calls the others."""
    self.view_panel.doKeywordChange(new_keyword, old_keyword)
    self.keyword_panel.doKeywordChange(new_keyword, old_keyword)
    self.task_panel.doKeywordChange(new_keyword, old_keyword)


def main():
  if len(sys.argv) > 1:
    filename = sys.argv[1]
  else:
    filename = TODO_TEXT_FILE

  todotxtfile = TodoTxtFile(filename)
  app = Application(todotxtfile.tasks)
  app.Run()


if __name__ == '__main__':
  main()
