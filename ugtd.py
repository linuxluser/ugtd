#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

import collections
import datetime
import inspect
import itertools
import os
import string
import sys
import time

import urwid


DIMENSIONS = ('projects', 'contexts', 'priority')
#TODO_TEXT_FILE = os.path.join(os.path.expanduser('~'), '.todo.txt')
TODO_TEXT_FILE = os.path.join(os.path.expanduser('~'), 'todo.test.txt')


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
        self._task = self.focus
        edit_widget = self._BuildEditWidget(self._task)
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
          if self._task.text != edit_widget.get_edit_text():
            # Get before/after properties and update the task itself
            old_properties = self._task.__dict__.copy()
            self._task.UpdateFromString(edit_widget.get_edit_text())
            new_properties = self._task.__dict__.copy()
            # Start a chain reaction so all widgets can deal with the changes
            self.tasklistbox.DoTaskChangeWork(old_properties, new_properties)

        self.contents[self.focus_position] = (self._task, ('pack', None))
        self._task = None
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
  """Panel to hold keywords.
  """

  def __init__(self, keywords_dict={}):
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
    if hasattr(self, '_keyword_change_callback'):
      new_keyword = self.GetSelectedKeyword()
      self._keyword_change_callback(new_keyword)
    return super(KeywordPanel, self).render(size, focus)

  def RegisterKeywordChangeCallback(self, callback):
    self._keyword_change_callback = callback

  def SwitchCategories(self, new_category):
    if new_category in self._listboxes:
      listbox = self._listboxes[new_category]
      self.padding_widget.original_widget = listbox
      self.border_widget.set_title(new_category.capitalize())
      self._selected_category = new_category

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
    text = self._listboxes[self._selected_category].focus.text
    if text == '--none--':
      return None
    else:
      return text


class TaskPanel(urwid.WidgetPlaceholder):

  DIMENSIONS = ('projects', 'contexts', 'priority')

  def __init__(self, tasks, keyword_panel):
    self.tasks = tasks
    self.keyword_panel = keyword_panel
    self._listboxes = {}

    # Tell the KeywordPanel what function to call when the keyword changes
    self.keyword_panel.RegisterKeywordChangeCallback(self._KeywordChange)

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
      for keyword in self.keyword_panel.GetKeywords(category):
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

  def SelectView(self, category, grouping):
    self.keyword_panel.SwitchCategories(category)
    keyword = self.keyword_panel.GetSelectedKeyword()
    listbox = self._listboxes[(category, keyword, grouping)]
    self.padding_widget.original_widget = listbox

    # Sorting dimension is whatever is not our category or grouping dimension
    sorting = set(DIMENSIONS).difference((category, grouping)).pop()

    self.category = category
    self.grouping = grouping
    self.sorting = sorting

    self._SetTitle()

  def _SetTitle(self):
    title = 'Tasks by %s' % self.grouping.capitalize()
    self.border_widget.set_title(title)

  def _KeywordChange(self, new_keyword):
    listbox = self._listboxes[(self.category, new_keyword, self.grouping)]
    self.padding_widget.original_widget = listbox
    self._SetTitle()


class ViewPanel(Border):
  """Top panel with selectable 'views' on Task data.

  The ViewPanel has a reference to the TaskPanel so that when the view is
  changed, that event can be passed on to the TaskPanel to react to it.
  """

  #            LABEL   -  CATEGORY  -  GROUPING
  VIEWS = [(u'[Pri/Ctx]', 'priority', 'contexts'),
           (u'[Prj/Ctx]', 'projects', 'contexts'),
           (u'[Prj/Pri]', 'projects', 'priority'),
           (u'[Ctx/Prj]', 'contexts', 'projects'),
           (u'[Ctx/Pri]', 'contexts', 'priority'),
           (u'[Pri/Prj]', 'priority', 'projects')]

  def __init__(self, task_panel):
    #self.keyword_panel = keyword_panel
    self.task_panel = task_panel

    self.text_widgets = [urwid.Text(('normal', V[0])) for V in ViewPanel.VIEWS]
    widget = urwid.Columns([(11, t) for t in self.text_widgets])
    widget = urwid.Padding(widget, left=1)
    super(ViewPanel, self).__init__(widget)

    self._selected_index = -1
    self.SelectView(1)

  def SelectView(self, view):
    index = view - 1
    if self._selected_index == index:
      return
    if index in range(len(self.text_widgets)):
      # Select new view
      old_widget = self.text_widgets[self._selected_index]
      new_widget = self.text_widgets[index]
      old_widget.set_text(('normal', old_widget.text))
      new_widget.set_text(('selected', new_widget.text))
      self._selected_index = index

      # Update TaskPanel (which updates KeywordPanel)
      label, category, grouping = ViewPanel.VIEWS[index]
      self.task_panel.SelectView(category, grouping)


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
  """Main application.
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
    self.keyword_panel = KeywordPanel(keywords)
    self.keyword_panel.SwitchCategories('priority')
    self.task_panel = TaskPanel(tasks, self.keyword_panel)
    self.task_panel.SelectView('priority', 'contexts')
    self.view_panel = ViewPanel(self.task_panel)
    columns = urwid.Columns([(30, self.keyword_panel), self.task_panel], focus_column=0)
    self.browser = urwid.Frame(columns, header=self.view_panel)

  def _UnhandledInput(self, key):
    if key == 'esc':
      raise urwid.ExitMainLoop()
    elif key.isdigit():
      self.view_panel.SelectView(int(key))

  def Run(self):
    self.main_loop = urwid.MainLoop(self.browser,
                                    palette=Application.PALETTE,
                                    unhandled_input=self._UnhandledInput)
    self.main_loop.run()


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
