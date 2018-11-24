#!/usr/bin/env python2.7

"""
Columbia W4111 Intro to Databases
Example Webserver

To run locally

    python server.py

Go to http://localhost:8111 in your browser


A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""

import os, arrow
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, session

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)



# XXX: The Database URI should be in the format of: 
#
#     postgresql://USER:PASSWORD@<IP_OF_POSTGRE_SQL_SERVER>/<DB_NAME>
#
# For example, if you had username ewu2493, password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://ewu2493:foobar@<IP_OF_POSTGRE_SQL_SERVER>/postgres"
#
# For your convenience, we already set it to the class database

# Use the DB credentials you received by e-mail
DB_USER = "ms5505"
DB_PASSWORD = "1ktc6r12"

DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"

DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/w4111"


#
# This line creates a database engine that knows how to connect to the URI above
#
engine = create_engine(DATABASEURI)


# Here we create a test table and insert some values in it
engine.execute("""DROP TABLE IF EXISTS test;""")
engine.execute("""CREATE TABLE IF NOT EXISTS test (
  id serial,
  name text
);""")
engine.execute("""INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace');""")



@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request

  The variable g is globally accessible
  """
  try:
    g.conn = engine.connect()
  except:
    print "uh oh, problem connecting to database"
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to e.g., localhost:8111/foobar/ with POST or GET then you could use
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
# 
# see for routing: http://flask.pocoo.org/docs/0.10/quickstart/#routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#
@app.route('/index')
def index():
  """
  request is a special object that Flask provides to access web request information:

  request.method:   "GET" or "POST"
  request.form:     if the browser submitted a form, this contains the data in the form
  request.args:     dictionary of URL arguments e.g., {a:1, b:2} for http://localhost?a=1&b=2

  See its API: http://flask.pocoo.org/docs/0.10/api/#incoming-request-data
  """

  # DEBUG: this is debugging code to see what request looks like
  print request.args


  #
  # example of a database query
  #
  cursor = g.conn.execute("SELECT name FROM test")
  names = []
  for result in cursor:
    names.append(result['name'])  # can also be accessed using result[0]
  cursor.close()

  #
  # Flask uses Jinja templates, which is an extension to HTML where you can
  # pass data to a template and dynamically generate HTML based on the data
  # (you can think of it as simple PHP)
  # documentation: https://realpython.com/blog/python/primer-on-jinja-templating/
  #
  # You can see an example template in templates/index.html
  #
  # context are the variables that are passed to the template.
  # for example, "data" key in the context variable defined below will be 
  # accessible as a variable in index.html:
  #
  #     # will print: [u'grace hopper', u'alan turing', u'ada lovelace']
  #     <div>{{data}}</div>
  #     
  #     # creates a <div> tag for each element in data
  #     # will print: 
  #     #
  #     #   <div>grace hopper</div>
  #     #   <div>alan turing</div>
  #     #   <div>ada lovelace</div>
  #     #
  #     {% for n in data %}
  #     <div>{{n}}</div>
  #     {% endfor %}
  #
  context = dict(data = names)

  #
  # render_template looks in the templates/ folder for files.
  # for example, the below file reads template/index.html
  #
  return render_template("index.html", **context)

#
# This is an example of a different path.  You can see it at
# 
#     localhost:8111/another
#
# notice that the functio name is another() rather than index()
# the functions for each app.route needs to have different names
#
 
## NOTES ##  

# context = dict(variableInHTML = variableHere, variable2InHTML = variable2Here) --> passed to 1 template
# render return_template('home.html', **context)

# cursor = g.conn.execute("""SQL COMMANDS HERE;""")     this is an array of all the result 
# cursor.close()

@app.route('/')
def home():
  if not session.get('logged_in'):
    return render_template('login.html')
  else:
    ## pull all groups the user belongs to
    se = session.get('uid')
    before_request()
    cursor = g.conn.execute("""SELECT * from users_in_groups INNER JOIN groups ON users_in_groups.gid = groups.gid;""")
    groups = []
    for result in cursor:
      if result['uid'] == session['uid']:
        gr = []
        gr.append(result['gid'])
        gr.append(result['name'])
        groups.append(gr)
    cursor.close()
    context = dict(uid = session['uid'], 
      user_name = session['name'],
      groups = groups)
    return render_template('home.html', **context)

@app.route('/', methods=['POST'])
def login():
  before_request()
  cursor = g.conn.execute("""SELECT * FROM users;""")
  foundMatch = False
  pw = ''
  for result in cursor:
    if result['email'] == request.form['email']:
      foundMatch = True
      session['uid'] = result['uid']
      session['name'] = result['name']
      pw = result['password'] # add use of Flask session capabilities to store current user name/id
  if foundMatch == False:
    print('email not found. Please create an account') # need to give option to redirect and create account on login.html
  else:
    if pw == request.form['password']:
      session['logged_in'] = True
    else:
      print('wrong password')
  cursor.close()
  return home()

@app.route('/createAccount')
def createAccount():
  return render_template('createAccount.html')

@app.route('/group/<gid>')

### NOTE: uid is not currently an attribute in groups so finding the owner will fail until we add it
def group(gid):
  if not session.get('logged_in'):
    return render_template('login.html')
  else:
    # get group name (again)
    groupname = ''
    ownerid = 0
    cursor = g.conn.execute("""SELECT * FROM groups;""")
    for result in cursor:
      if int(result['gid']) == int(gid):
        groupname = result['name']
        #ownerid = result['uid']
    cursor.close()

    # get list of all members
    members = [] # uid, name
    owner = ''
    cursor0 = g.conn.execute("""SELECT * FROM users_in_groups INNER JOIN users ON users_in_groups.uid = users.uid;""")
    for result in cursor0:
      if int(result['gid']) == int(gid):
        member = []
        member.append(result['uid'])
        member.append(str(result['name']))
        members.append(member)
        if result['uid'] == ownerid:
          owner = result['name']
    cursor0.close()

    # get all wishlists
    wishlists = [] # wid, uid, name
    cursor1 = g.conn.execute("""SELECT * FROM wishlist_in_group INNER JOIN user_adds_wishlist ON wishlist_in_group.wid = user_adds_wishlist.wid
      INNER JOIN users ON user_adds_wishlist.uid = users.uid;""")
    for result in cursor1:
      if int(result['gid']) == int(gid):
        wishlist = []
        wishlist.append(result['wid'])
        wishlist.append(result['uid'])
        wishlist.append(result['name'])
        wishlists.append(wishlist)  
    cursor1.close()

    context = dict(gid = gid, owner = owner, members = members, wishlists = wishlists, groupname = groupname)
    return render_template('group.html', **context)

@app.route('/group/<gid>/wishlist/<wid>')
def show_wishlist(gid, wid):
  if not session.get('logged_in'):
    return render_template('login.html')
  else:
    session_uid = session['uid']

    # get wishlist author's name
    author_name = ''
    author_uid = 0
    cursor = g.conn.execute("""SELECT * FROM user_adds_wishlist INNER JOIN users ON user_adds_wishlist.uid = users.uid;""")
    for result in cursor:
      if int(result['wid']) == int(wid):
        author_name = result['name']
        author_uid = result['uid']
    cursor.close()

    # get items in wishlist (using items_in_wishlist join user_adds_items)
    items = []
    cursor0 = g.conn.execute("""SELECT * from items_in_wishlist inner join user_adds_items on items_in_wishlist.iid = user_adds_items.iid;""")
    # result: wid id uid item name(description) added uid 
    for result in cursor0:
      if int(result['wid']) == int(wid):
        item = []
        item.append(result['iid'])
        item.append(result['iname'])
        items.append(item)
    cursor0.close()

    table = []
    # get comments UNLESS user is viewing her own wishlist
    if int(session_uid) != int(author_uid):
      comments = []
      cursor1 = g.conn.execute("""SELECT * from items_in_wishlist inner join user_post_comments 
        on items_in_wishlist.iid = user_post_comments.iid inner join users on user_post_comments.cuid = users.uid;""")
      for result in cursor1:
        if int(result['wid']) == int(wid): # for each row relating to this wishlist
          comment = [] # cuid iid body name
          comment.append(result['cuid'])
          comment.append(result['iid'])
          comment.append(result['body'])
          comment.append(result['name'])
          comment.append(result['cid'])
          comments.append(comment)
      
      # sort comments into table row stuff
      
      for i in items:
        tablerow = []
        tablerow.append(i)
        for c in comments:
          if c[1] == i[0]: #if item id of comment matches item id of item
            tablerow.append(c)
            # could potentially make this faster by removing comment c after it's added to a table row
        table.append(tablerow)

      context = dict(gid = gid, wid = wid, name = author_name, table = table, uid = session_uid)
      return render_template('wishlist.html', **context)
    
    else:
      for i in items:
        tablerow = []
        tablerow.append(i)
        table.append(tablerow)
      context = dict(gid = gid, wid = wid, name = author_name, table = table)
      return render_template('wishlist_mine.html', **context)

@app.route('/group/<gid>/wishlist/<wid>/i', methods=['POST'])
def add_item_to_wishlist(gid, wid):
  if not session.get('logged_in'):
    return render_template('login.html')
  else:
    # get most recent iid
    cursor = g.conn.execute("""SELECT MAX(iid) FROM user_adds_items;""")
    for result in cursor:
      iid = int(result[0]) + 1
    cursor.close()

    # create item
    uid = session.get('uid')
    it = request.form['item']
    added_date = arrow.now().format('YYYY-MM-DD')
    cmd0 = 'INSERT INTO user_adds_items (iid, iname, added_date, uid) VALUES (:iid, :iname, :added_date, :uid);'
    cursor0 = g.conn.execute(text(cmd0), iid = iid, iname = it, added_date = added_date, uid = uid)
    cursor0.close()

    # add item to wishlist
    cmd1 = 'INSERT INTO items_in_wishlist (wid, iid, uid) VALUES (:wid, :iid, :uid);'
    cursor1 = g.conn.execute(text(cmd1), wid = wid, iid = iid, uid = uid)
    cursor1.close()

    return show_wishlist(gid, wid)

@app.route('/group/<gid>/wishlist/<wid>/d/<iid>')
def remove_item_from_wishlist(gid, wid, iid):
  if not session.get('logged_in'):
    return render_template('login.html')
  else:
    # remove from items_in_wishlist
    cmd = 'DELETE FROM items_in_wishlist WHERE iid = :id;'
    cursor = g.conn.execute(text(cmd), id = iid)
    cursor.close()
    # remove from user_adds_items (which also removes from user_post_comments)
    cmd0 = 'DELETE FROM user_adds_items WHERE iid = :id;'
    cursor0 = g.conn.execute(text(cmd0), id = iid)
    cursor0.close()
    return show_wishlist(gid, wid)

@app.route('/group/<gid>/wishlist/<wid>/c/<iid>', methods=['POST'])
def comment_on_item(gid, wid, iid):
  if not session.get('logged_in'):
    return render_template('login.html')
  else:
    
    # get new cid
    cursor = g.conn.execute("""SELECT MAX(cid) FROM user_post_comments;""")
    for result in cursor:
      cid = int(result[0]) + 1
    cursor.close()

    # get cuid
    cuid = session.get('uid')

    # get uid
    uid = 0
    cmd0 = 'SELECT uid from user_adds_items where iid = :id'
    cursor0 = g.conn.execute(text(cmd0), id = iid)
    for result in cursor0:
      uid = result[0]
    cursor0.close()

    # get post_date
    post_date = arrow.now().format('YYYY-MM-DD')

    # get body
    body = request.form['comment']

    # add the comment
    cmd1 = 'INSERT INTO user_post_comments (uid, iid, cuid, cid, body, post_date) VALUES (:uid, :iid, :cuid, :cid, :body, :post_date);'
    cursor1 = g.conn.execute(text(cmd1), uid = uid, iid = iid, cuid = cuid, cid = cid, body = body, post_date = post_date)
    cursor1.close()

    return show_wishlist(gid, wid)

@app.route('/group/<gid>/wishlist/<wid>/dc/<cid>', methods=['POST'])
def delete_comment(gid, wid, cid):
  if not session.get('logged_in'):
    return render_template('login.html')
  else:
    # remove comment
    cmd = 'DELETE FROM user_post_comments WHERE cid = :cid;'
    cursor = g.conn.execute(text(cmd), cid = cid)
    cursor.close()
    return show_wishlist(gid, wid)

@app.route('/another')
def another():
  return render_template("anotherfile.html")

# Example of adding new data to the database
@app.route('/add', methods=['POST'])
def add():
  name = request.form['name']
  print name
  cmd = 'INSERT INTO test(name) VALUES (:name1), (:name2)';
  g.conn.execute(text(cmd), name1 = name, name2 = name);
  return redirect('/')

if __name__ == "__main__":
  app.secret_key = os.urandom(12)
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=7111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using

        python server.py

    Show the help text using

        python server.py --help

    """

    HOST, PORT = host, port
    print "running on %s:%d" % (HOST, PORT)
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()
