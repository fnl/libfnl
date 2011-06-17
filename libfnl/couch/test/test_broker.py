"""
Virtually equal to the original code by Christopher Lenz for CouchDB-Python.
"""

__author__ = 'Christopher Lenz'

from datetime import datetime
import os
import os.path
import shutil
from io import StringIO
import time
import tempfile
import threading
import unittest
import urllib.parse

from libfnl.couch import broker, network
from libfnl.couch import testutil
network.CACHE_SIZE = 2, 3

class ServerTestCase(testutil.TempDatabaseMixin, unittest.TestCase):

    def test_init_with_resource(self):
        sess = network.Session()
        res = network.Resource(broker.COUCHDB_URL, sess)
        serv = broker.Server(url=res)
        serv.config()

    def test_init_with_session(self):
        sess = network.Session()
        serv = broker.Server(session=sess)
        serv.config()
        self.assertTrue(serv.resource.session is sess)

    def test_exists(self):
        self.assertTrue(broker.Server())
        self.assertFalse(broker.Server('http://localhost:9999'))

    def test_repr(self):
        repr(self.server)

    def test_server_vars(self):
        version = self.server.version()
        self.assertTrue(isinstance(version, str))
        config = self.server.config()
        self.assertTrue(isinstance(config, dict))
        tasks = self.server.tasks()
        self.assertTrue(isinstance(tasks, list))

    def test_server_stats(self):
        stats = self.server.stats()
        self.assertTrue(isinstance(stats, dict))
        stats = self.server.stats('httpd/requests')
        self.assertTrue(isinstance(stats, dict))
        self.assertEqual(7, len(stats), stats)
        self.assertEqual('number of HTTP requests', stats['description'])

    def test_get_db_missing(self):
        self.assertRaises(network.ResourceNotFound,
                          lambda: self.server['couchdb-python/missing'])

    def test_create_db_conflict(self):
        name, db = self.temp_db()
        self.assertRaises(network.PreconditionFailed, self.server.create,
                          name)

    def test_delete_db(self):
        name, db = self.temp_db()
        assert name in self.server
        self.del_db(name)
        assert name not in self.server

    def test_delete_db_missing(self):
        self.assertRaises(network.ResourceNotFound, self.server.delete,
                          'couchdb-python/missing')

    def test_replicate(self):
        aname, a = self.temp_db()
        bname, b = self.temp_db()
        id, rev = a.save({'test': 'a'})
        result = self.server.replicate(aname, bname)
        self.assertEquals(result['ok'], True)
        self.assertEquals(b[id]['test'], 'a')

        doc = b[id]
        doc['test'] = 'b'
        b.bulk([doc])
        self.server.replicate(bname, aname)
        self.assertEquals(a[id]['test'], 'b')
        self.assertEquals(b[id]['test'], 'b')

    def test_replicate_continuous(self):
        aname, a = self.temp_db()
        bname, b = self.temp_db()
        result = self.server.replicate(aname, bname, continuous=True)
        self.assertEquals(result['ok'], True)
        version = tuple(int(i) for i in self.server.version().split('.')[:2])
        if version >= (0, 10):
            self.assertTrue('_local_id' in result)

    def test_iter(self):
        aname, a = self.temp_db()
        bname, b = self.temp_db()
        dbs = list(self.server)
        self.assertTrue(aname in dbs)
        self.assertTrue(bname in dbs)

    def test_len(self):
        self.temp_db()
        self.temp_db()
        self.assertTrue(len(self.server) >= 2)

    def test_uuids(self):
        ls = self.server.uuids()
        assert type(ls) == list
        ls = self.server.uuids(count=10)
        assert type(ls) == list and len(ls) == 10


class DatabaseTestCase(testutil.TempDatabaseMixin, unittest.TestCase):

    def test_save_new(self):
        doc = {'foo': 'bär'}
        id, rev = self.db.save(doc)
        self.assertTrue(id is not None)
        self.assertTrue(rev is not None)
        self.assertEqual((id, rev), (doc['_id'], doc['_rev']))
        doc = self.db.get(id)
        self.assertEqual(doc['foo'], 'bär')

    def test_save_new_with_id(self):
        doc = {'_id': 'föö'}
        id, rev = self.db.save(doc)
        self.assertTrue(doc['_id'] == id == 'föö')
        self.assertEqual(doc['_rev'], rev)

    def test_save_existing(self):
        doc = {}
        id_rev_old = self.db.save(doc)
        doc['föö'] = True
        id_rev_new = self.db.save(doc)
        self.assertTrue(doc['_rev'] == id_rev_new[1])
        self.assertTrue(id_rev_old[1] != id_rev_new[1])

    def test_save_new_batch(self):
        doc = {'_id': 'föö'}
        id, rev = self.db.save(doc, batch='ok')
        self.assertTrue(rev is None)
        self.assertTrue('_rev' not in doc)

    def test_save_existing_batch(self):
        doc = {'_id': 'föö'}
        self.db.save(doc)
        id_rev_old = self.db.save(doc)
        id_rev_new = self.db.save(doc, batch='ok')
        self.assertTrue(id_rev_new[1] is None)
        self.assertEqual(id_rev_old[1], doc['_rev'])

    def test_exists(self):
        self.assertTrue(self.db)
        self.assertFalse(bool(broker.Database('couchdb-python/missing')))

    def test_name(self):
        # Access name assigned during creation.
        name, db = self.temp_db()
        self.assertTrue(db.name == name)
        # Access lazily loaded name,
        self.assertTrue(broker.Database(db.resource.url).name == name)

    def test_commit(self):
        self.assertTrue(self.db.commit() is True)

    def test_create_large_doc(self):
        self.db['föö'] = {'dätä': '0123456789' * 110 * 1024} # 10 MB
        self.assertEqual('föö', self.db['föö']['_id'])

    def test_doc_id_quoting(self):
        self.db['föö/bär'] = {'föö': 'bär'}
        self.assertEqual('bär', self.db['föö/bär']['föö'])
        del self.db['föö/bär']
        self.assertEqual(None, self.db.get('föö/bär'))

    def test_unicode(self):
        self.db['føø'] = {'bår': 'Iñtërnâtiônàlizætiøn', 'baz': 'ASCII'}
        self.assertEqual('Iñtërnâtiônàlizætiøn', self.db['føø']['bår'])
        self.assertEqual('ASCII', self.db['føø']['baz'])

    def test_disallow_nan(self):
        try:
            self.db['foo'] = {'number': float('nan')}
            self.fail('Expected ValueError')
        except ValueError:
            pass

    def test_disallow_none_id(self):
        deldoc = lambda: self.db.delete({'_id': None, '_rev': None})
        self.assertRaises(ValueError, deldoc)

    def test_doc_revs(self):
        doc = {'bar': 42}
        self.db['foo'] = doc
        old_rev = doc['_rev']
        doc['bar'] = 43
        self.db['foo'] = doc
        new_rev = doc['_rev']

        new_doc = self.db.get('foo')
        self.assertEqual(new_rev, new_doc['_rev'])
        new_doc = self.db.get('foo', rev=new_rev)
        self.assertEqual(new_rev, new_doc['_rev'])
        old_doc = self.db.get('foo', rev=old_rev)
        self.assertEqual(old_rev, old_doc['_rev'])

        revs = [i for i in self.db.revisions('foo')]
        self.assertEqual(2, len(revs), revs)
        self.assertEqual(new_rev, revs[0]['_rev'])
        self.assertEqual(old_rev, revs[1]['_rev'])
        gen = self.db.revisions('crap')
        self.assertRaises(network.ResourceNotFound, lambda: next(gen))

        self.assertTrue(self.db.compact())
        while self.db.info()['compact_running']:
            pass

        # 0.10 responds with 404, 0.9 responds with 500, same content
        doc = 'fail'
        try:
            doc = self.db.get('foo', rev=old_rev)
        except network.ServerError:
            doc = None
        assert doc is None

    def test_attachment_crud(self):
        doc = {'bar': 42}
        self.db['foo'] = doc
        old_rev = doc['_rev']

        self.db.saveAttachment(doc, 'Foo bar', 'foo.txt', 'text/plain')
        self.assertNotEquals(old_rev, doc['_rev'])

        doc = self.db['foo']
        attachment = doc['_attachments']['foo.txt']
        self.assertEqual(len('Foo bar'), attachment['length'])
        self.assertEqual('text/plain; charset=iso-8859-1', attachment['content_type'])

        self.assertEqual('Foo bar',
                         self.db.getAttachment(doc, 'foo.txt').data)
        self.assertEqual('Foo bar',
                         self.db.getAttachment('foo', 'foo.txt').data)

        # check encoding
        self.db.saveAttachment(doc, 'Föö bar', 'foo.txt', 'text/plain')
        self.assertEqual('Föö bar',
                         self.db.getAttachment('foo', 'foo.txt').data)
        # Ups - the next one is a bug in CouchDB prior to 1.1:
        # Couch cannot save attachment with non-ASCII chars in the file name!
        # self.db.saveAttachment(doc, 'Foo bar', 'föö.txt', 'text/plain')
        # self.assertEqual('Foo bar',
        #                   self.db.getAttachment('foo', 'föö.txt').data)

        old_rev = doc['_rev']
        self.db.deleteAttachment(doc, 'foo.txt')
        self.assertNotEquals(old_rev, doc['_rev'])
        self.assertEqual(None, self.db['foo'].get('_attachments'))

    def test_attachment_crud_with_files(self):
        doc = {'bar': 42}
        self.db['foo'] = doc
        old_rev = doc['_rev']
        fileobj = StringIO('Foo bar baz')

        self.db.saveAttachment(doc, fileobj, 'foo.txt')
        self.assertNotEquals(old_rev, doc['_rev'])

        doc = self.db['foo']
        attachment = doc.attachments['foo.txt']
        self.assertEqual(len('Foo bar baz'), attachment['length'])
        self.assertEqual('text/plain; charset=iso-8859-1', attachment['content_type'])

        self.assertEqual('Foo bar baz',
                         self.db.getAttachment(doc, 'foo.txt').data)
        self.assertEqual('Foo bar baz',
                         self.db.getAttachment('foo', 'foo.txt').data)

        old_rev = doc['_rev']
        self.db.deleteAttachment(doc, 'foo.txt')
        self.assertNotEquals(old_rev, doc['_rev'])
        self.assertEqual(None, self.db['foo'].get('_attachments'))

    def test_empty_attachment(self):
        doc = {}
        self.db['foo'] = doc
        old_rev = doc['_rev']

        self.db.saveAttachment(doc, '', 'empty.txt')
        self.assertNotEquals(old_rev, doc['_rev'])

        doc = self.db['foo']
        attachment = doc['_attachments']['empty.txt']
        self.assertEqual(0, attachment['length'])

    def test_default_attachment(self):
        doc = {}
        self.db['foo'] = doc
        self.assertTrue(self.db.getAttachment(doc, 'missing.txt') is None)
        sentinel = object()
        self.assertTrue(self.db.getAttachment(doc, 'missing.txt', sentinel) is sentinel)

    def test_attachment_from_fs(self):
        tmpdir = tempfile.mkdtemp()
        tmpfile = os.path.join(tmpdir, 'test.txt')
        f = open(tmpfile, 'w')
        f.write('Hello!')
        f.close()
        doc = {}
        self.db['foo'] = doc
        self.db.saveAttachment(doc, open(tmpfile))
        doc = self.db.get('foo')
        self.assertEqual('text/plain; charset=US-ASCII', doc.attachments['test.txt']['content_type'])
        shutil.rmtree(tmpdir)

    def test_attachment_no_filename(self):
        doc = {}
        self.db['foo'] = doc
        self.assertRaises(ValueError, self.db.saveAttachment, doc, '')

    def test_json_attachment(self):
        doc = {}
        self.db['foo'] = doc
        self.db.saveAttachment(doc, '{}', 'test.json', 'application/json')
        self.assertEquals('{}', self.db.getAttachment(doc, 'test.json').data)

    def test_include_docs(self):
        doc = {'foo': 42, 'bar': 40}
        self.db['foo'] = doc

        rows = list(self.db.query(
            'function(doc) { emit(doc._id, null); }',
            include_docs=True
        ))
        self.assertEqual(1, len(rows))
        self.assertEqual(doc, rows[0].doc)

    def test_query_multi_get(self):
        for i in range(1, 6):
            self.db.save({'i': i})
        res = list(self.db.query('function(doc) { emit(doc.i, null); }',
                                 doc_ids=list(range(1, 6, 2))))
        self.assertEqual(3, len(res), res)

        for idx, i in enumerate(range(1, 6, 2)):
            self.assertEqual(i, res[idx].key,
                             "key={} expected, got {}".format(i, res[idx]))

    def test_bulk_update_conflict(self):
        docs = [
            dict(type='Person', name='John Doe'),
            dict(type='Person', name='Mary Jane'),
            dict(type='City', name='Gotham City')
        ]
        self.db.bulk(docs)

        # update the first doc to provoke a conflict in the next bulk update
        doc = docs[0].copy()
        self.db[doc['_id']] = doc

        results = self.db.bulk(docs)
        self.assertEqual(False, results[0][0])
        assert isinstance(results[0][2], network.ResourceConflict)

    def test_bulk_update_all_or_nothing(self):
        docs = [
            dict(type='Person', name='John Doe'),
            dict(type='Person', name='Mary Jane'),
            dict(type='City', name='Gotham City')
        ]
        self.db.bulk(docs)

        # update the first doc to provoke a conflict in the next bulk update
        doc = docs[0].copy()
        doc['name'] = 'Jane Doe'
        self.db[doc['_id']] = doc

        results = self.db.bulk(docs, strict=True)
        self.assertEqual(True, results[0][0])

        doc = self.db.get(doc['_id'], conflicts=True)
        assert '_conflicts' in doc
        revs = self.db.get(doc['_id'], open_revs='all')
        assert len(revs) == 2

    def test_bulk_update_bad_doc(self):
        self.assertRaises(TypeError, self.db.bulk, [object()])

    def test_copy_doc(self):
        self.db['foo'] = {'status': 'testing'}
        result = self.db.copy('foo', 'bar')
        self.assertEqual(result, self.db['bar'].rev)

    def test_copy_doc_conflict(self):
        self.db['bar'] = {'status': 'idle'}
        self.db['foo'] = {'status': 'testing'}
        self.assertRaises(network.ResourceConflict, self.db.copy, 'foo', 'bar')

    def test_copy_doc_overwrite(self):
        self.db['bar'] = {'status': 'idle'}
        self.db['foo'] = {'status': 'testing'}
        result = self.db.copy('foo', self.db['bar'])
        doc = self.db['bar']
        self.assertEqual(result, doc.rev)
        self.assertEqual('testing', doc['status'])

    def test_copy_doc_srcobj(self):
        self.db['foo'] = {'status': 'testing'}
        self.db.copy(self.db['foo'], 'bar')
        self.assertEqual('testing', self.db['bar']['status'])

    def test_copy_doc_destobj_norev(self):
        self.db['foo'] = {'status': 'testing'}
        self.db.copy('foo', {'_id': 'bar'})
        self.assertEqual('testing', self.db['bar']['status'])

    def test_copy_doc_src_baddoc(self):
        self.assertRaises(TypeError, self.db.copy, object(), 'bar')

    def test_copy_doc_dest_baddoc(self):
        self.assertRaises(TypeError, self.db.copy, 'foo', object())

    def test_changes(self):
        self.db['foo'] = {'bar': True}
        self.assertEqual(self.db.changes(since=0)[0], 1)
        first = next(self.db.changes(feed='continuous'))
        self.assertEqual(first['seq'], 1)
        self.assertEqual(first['id'], 'foo')

    def test_changes_conn_usable(self):
        # Consume a changes feed to get a used connection in the pool.
        list(self.db.changes(feed='continuous', timeout=0))
        # Try using the connection again to make sure the connection was left
        # in a good state from the previous request.
        self.assertTrue(self.db.info()['doc_count'] == 0)

    def test_changes_heartbeat(self):
        def wakeup():
            time.sleep(.3)
            self.db.save({})
        threading.Thread(target=wakeup).start()
        for _ in self.db.changes(feed='continuous', heartbeat=100):
            break

    def test_purge(self):
        doc = {'a': 'b'}
        self.db['foo'] = doc
        self.assertEqual(self.db.purge([doc])[0], 1)

    def test_json_date_encoding(self):
        now = datetime.now()
        doc = {'now': now}
        id, _ = self.db.save(doc)
        doc = self.db[id]
        self.assertEqual(doc["now"], now.isoformat())


class ViewTestCase(testutil.TempDatabaseMixin, unittest.TestCase):

    def test_row_object(self):

        rows = list(self.db.view('_all_docs', doc_ids=['blah']))
        self.assertEqual("[<Row key='blah', error='not_found'>]", repr(rows))
        self.assertEqual(None, rows[0].id)
        self.assertEqual('blah', rows[0].key)
        self.assertEqual(None, rows[0].value)
        self.assertEqual('not_found', rows[0].error)

        self.db.save({'_id': 'xyz', 'föö': 'bär'})
        rows = list(self.db.view('_all_docs', doc_ids=['xyz']))
        self.assertEqual(rows[0].id, 'xyz')
        self.assertEqual(rows[0].key, 'xyz')
        self.assertEqual(list(rows[0].value.keys()), ['rev'])
        self.assertEqual(rows[0].error, None)

    def test_view_multi_get(self):
        for i in range(1, 6):
            self.db.save({'i': i})
        self.db['_design/test'] = {
            'language': 'javascript',
            'views': {
                'multi_key': {'map': 'function(doc) { emit(doc.i, null); }'}
            }
        }

        res = list(self.db.view('test/multi_key', doc_ids=list(range(1, 6, 2))))
        self.assertEqual(3, len(res))
        for idx, i in enumerate(list(range(1, 6, 2))):
            self.assertEqual(i, res[idx].key)

    def test_ddoc_info(self):
        self.db['_design/test'] = {
            'language': 'javascript',
            'views': {
                'test': {'map': 'function(doc) { emit(doc.type, null); }'}
            }
        }
        info = self.db.info('test')
        self.assertEqual(info['view_index']['compact_running'], False)

    def test_view_compaction(self):
        for i in range(1, 6):
            self.db.save({'i': i})
        self.db['_design/test'] = {
            'language': 'javascript',
            'views': {
                'multi_key': {'map': 'function(doc) { emit(doc.i, null); }'}
            }
        }

        self.db.view('test/multi_key')
        self.assertTrue(self.db.compact('test'))

    def test_view_cleanup(self):
        for i in range(1, 6):
            self.db.save({'i': i})

        self.db['_design/test'] = {
            'language': 'javascript',
            'views': {
                'multi_key': {'map': 'function(doc) { emit(doc.i, null); }'}
            }
        }
        self.db.view('test/multi_key')

        ddoc = self.db['_design/test']
        ddoc['views'] = {
            'ids': {'map': 'function(doc) { emit(doc._id, null); }'}
        }
        self.db.bulk([ddoc])
        self.db.view('test/ids')
        self.assertTrue(self.db.cleanup())

    def test_view_function_objects(self):
        if 'python' not in self.server.config()['query_servers']:
            return

        for i in range(1, 4):
            self.db.save({'i': i, 'j':2*i})

        def map_fun(doc):
            yield doc['i'], doc['j']
        res = list(self.db.query(map_fun, language='python'))
        self.assertEqual(3, len(res))
        for idx, i in enumerate(list(range(1,4))):
            self.assertEqual(i, res[idx].key)
            self.assertEqual(2*i, res[idx].value)

        def reduce_fun(keys, values):
            return sum(values)
        res = list(self.db.query(map_fun, reduce_fun, 'python'))
        self.assertEqual(1, len(res))
        self.assertEqual(12, res[0].value)

    def test_init_with_resource(self):
        self.db['foo'] = {}
        view = broker.PermanentView(self.db.resource('_all_docs').url, '_all_docs')
        self.assertEquals(len(list(view())), 1)

    def test_iter_view(self):
        self.db['föö'] = {"föö": "bär"}
        view = broker.PermanentView(self.db.resource('_all_docs').url, '_all_docs')
        rows = list(view)
        self.assertEqual(1, len(rows))
        self.assertEqual("föö", rows[0].id)
        self.assertEqual("föö", rows[0].key)

    def test_tmpview_repr(self):
        mapfunc = "function(doc) {emit(null, null);}"
        view = broker.TemporaryView(self.db.resource('_temp_view'), mapfunc)
        self.assertTrue('TemporaryView' in repr(view))
        self.assertTrue(mapfunc in repr(view))

    def test_wrapper_iter(self):
        class Wrapper(object):
            def __init__(self, _):
                pass
        self.db['foo'] = {}
        self.assertTrue(isinstance(list(self.db.view('_all_docs', wrapper=Wrapper))[0], Wrapper))

    def test_wrapper_rows(self):
        class Wrapper(object):
            def __init__(self, _):
                pass
        self.db['foo'] = {}
        self.assertTrue(isinstance(next(self.db.view('_all_docs', wrapper=Wrapper).rows), Wrapper))

    def test_properties(self):
        for attr in ['rows', 'total_rows', 'offset']:
            self.assertTrue(getattr(self.db.view('_all_docs'), attr) is not None)

    def test_rowrepr(self):
        self.db['foo'] = {}
        rows = list(self.db.query("function(doc) {emit(null, 1);}"))
        self.assertTrue('Row' in repr(rows[0]))
        self.assertTrue('id' in repr(rows[0]))
        rows = list(self.db.query("function(doc) {emit(null, 1);}", "function(keys, values, combine) {return sum(values);}"))
        self.assertTrue('Row' in repr(rows[0]))
        self.assertTrue('id' not in repr(rows[0]))


class ShowListTestCase(testutil.TempDatabaseMixin, unittest.TestCase):

    show_func = """
        function(doc, req) {
            return {"body": req.id + ":" + (req.query.r || "<default>")};
        }
        """

    list_func = """
        function(head, req) {
            start({headers: {'Content-Type': 'text/csv'}});
            if (req.query.include_header) {
                send('id' + '\\r\\n');
            }
            var row;
            while (row = getRow()) {
                send(row.id + '\\r\\n');
            }
        }
        """

    design_doc = {'_id': '_design/foo',
                  'shows': {'bar': show_func},
                  'views': {'by_id': {'map': "function(doc) {emit(doc._id, null)}"},
                            'by_name': {'map': "function(doc) {emit(doc.name, null)}"}},
                  'lists': {'list': list_func}}

    def setUp(self):
        super(ShowListTestCase, self).setUp()
        # Workaround for possible bug in CouchDB. Adding a timestamp avoids a
        # 409 Conflict error when pushing the same design doc that existed in a
        # now deleted database.
        design_doc = dict(self.design_doc)
        design_doc['timestamp'] = time.time()
        self.db.save(design_doc)
        self.db.bulk([{'_id': '1', 'name': 'one'}, {'_id': '2', 'name': 'two'}])

    def test_show_urls(self):
        self.assertEqual('null:<default>', str(self.db.show('_design/foo/_show/bar').data))
        self.assertEqual('null:<default>', str(self.db.show('foo/bar').data))

    def test_show_docid(self):
        self.assertEqual(self.db.show('foo/bar').data, 'null:<default>')
        self.assertEqual(self.db.show('foo/bar', '1').data, '1:<default>')
        self.assertEqual(self.db.show('foo/bar', '2').data, '2:<default>')

    def test_show_params(self):
        self.assertEqual(self.db.show('foo/bar', r='abc').data, 'null:abc')

    def test_list(self):
        self.assertEqual(str(self.db.list('foo/list', 'foo/by_id').data), '1\r\n2\r\n')
        self.assertEqual(self.db.list('foo/list', 'foo/by_id', include_header='true').data.read(), b'id\r\n1\r\n2\r\n')

    def test_list_keys(self):
        self.assertEqual(self.db.list('foo/list', 'foo/by_id', doc_ids=['1']).data.read(), b'1\r\n')

    def test_list_view_params(self):
        self.assertEqual(str(self.db.list('foo/list', 'foo/by_name', startkey='o', endkey='p').data), '1\r\n')
        data = self.db.list('foo/list', 'foo/by_name', descending=True).data
        items = tuple(map(int, data))
        self.assertEqual((2, 1), items)

class UpdateHandlerTestCase(testutil.TempDatabaseMixin, unittest.TestCase):
    update_func = """
        function(doc, req) {
          if (!doc) {
            if (req.id) {
              return [{_id : req.id}, "new doc"]
            }
            return [null, "empty doc"];
          }
          doc.name = "hello";
          return [doc, "hello doc"];
        }
    """

    design_doc = {'_id': '_design/foo',
                  'language': 'javascript',
                  'updates': {'bar': update_func}}

    def setUp(self):
        super(UpdateHandlerTestCase, self).setUp()
        # Workaround for possible bug in CouchDB. Adding a timestamp avoids a
        # 409 Conflict error when pushing the same design doc that existed in a
        # now deleted database.
        design_doc = dict(self.design_doc)
        design_doc['timestamp'] = time.time()
        self.db.save(design_doc)
        self.db.bulk([{'_id': 'existed', 'name': 'bar'}])

    def test_empty_doc(self):
        self.assertEqual(self.db.update('foo/bar').data, 'empty doc')

    def test_new_doc(self):
        self.assertEqual(self.db.update('foo/bar', 'new').data, 'new doc')

    def test_update_doc(self):
        self.assertEqual(self.db.update('foo/bar', 'existed').data, 'hello doc')

if __name__ == '__main__':
    unittest.main()
