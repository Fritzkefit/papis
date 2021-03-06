"""
This command is in an experimental stage but it might be useful for many
people.

Imagine you want to search for some papers online, but you don't want to
go into a browser and look for it. Explore gives you way to do this,
using several services available online, more should be coming on the way.

An excellent such resource is `crossref <https://crossref.org/>`_,
which you can use by using the subcommand crossref:

::

    papis explore crossref --author 'Freeman Dyson'

If you issue this command, you will see some text but basically nothing
will happen. This is because ``explore`` is conceived in such a way
as to concatenate commands, doing a simple

::

    papis explore crossref -h

will tell you which commands are available.
Let us suppose that you want to look for some documents on crossref,
say some papers of Schroedinger, and you want to store them into a bibtex
file called ``lib.bib``, then you could concatenate the commands
``crossref`` and ``export --bibtex`` as such

::

    papis explore crossref -a 'Schrodinger' export --bibtex lib.bib

This will store everything that you got from crossref in the file ``lib.bib``
and store in bibtex format. ``explore`` is much more flexible than that,
you can also pick just one document to store, for instance let's assume that
you don't want to store all retrieved documents but only one that you pick,
the ``pick`` command will take care of it

::

    papis explore crossref -a 'Schrodinger' pick export --bibtex lib.bib

notice how the ``pick`` command is situated before the ``export``.
More generally you could write something like

::

    papis explore \\
        crossref -a Schroedinger \\
        crossref -a Einstein \\
        arxiv -a 'Felix Hummel' \\
        export --yaml docs.yaml \\
        pick  \\
        export --bibtex specially-picked-document.bib

The upper command will look in crossref for documents authored by Schrodinger,
then also by Einstein, and will look on the arxiv for papers authored by Felix
Hummel. At the end, all these documents will be stored in the ``docs.yaml``.
After that we pick one document from them and store the information in
the file ``specially-picked-document.bib``, and we could go on and on.

If you want to follow-up on these documents and get them again to pick one,
you could use the ``yaml`` command to read in document information from a yaml
file, i.e., the previously created ``docs.yaml``

::

    papis explore \\
        yaml docs.yaml \\
        pick \\
        cmd 'papis scihub {doc[doi]}' \\
        cmd 'firefox {doc[url]}'

In this last example, we read the documents' information from ``docs.yaml`` and
pick a document, which then feed into the ``explore cmd`` command, that accepts
a papis formatting string to issue a general shell command.  In this case, the
picked document gets fed into the ``papis scihub`` command which tries to
download the document using ``scihub``, and also this very document is tried to
be opened by firefox (in case the document does have a ``url``).

Cli
^^^
.. click:: papis.commands.explore:cli
    :prog: papis explore
    :show-nested:
"""
import os
import papis.utils
import papis.commands
import papis.document
import papis.config
import papis.bibtex
import papis.strings
import papis.cli
import click
import logging
import papis.commands.add
import papis.commands.export
import papis.api
import papis.crossref


logger = logging.getLogger('explore')


@click.group("explore", invoke_without_command=False, chain=True)
@click.help_option('--help', '-h')
@click.pass_context
def cli(ctx):
    """
    Explore new documents using a variety of resources
    """
    ctx.obj = {'documents': []}


@cli.command('arxiv')
@click.pass_context
@click.help_option('--help', '-h')
@click.option('--query', '-q', default=None)
@click.option('--author', '-a', default=None)
@click.option('--title', '-t', default=None)
@click.option('--abstract', default=None)
@click.option('--comment', default=None)
@click.option('--journal', default=None)
@click.option('--report-number', default=None)
@click.option('--category', default=None)
@click.option('--id-list', default=None)
@click.option('--page', default=None)
@click.option('--max', '-m', default=20)
def arxiv(ctx, query, author, title, abstract, comment,
          journal, report_number, category, id_list, page, max):
    """
    Look for documents on ArXiV.org.

    Examples of its usage are

        papis explore arxiv -a 'Hummel' -m 100 arxiv -a 'Garnet Chan' pick

    If you want to search for the exact author name 'John Smith', you should
    enclose it in extra quotes, as in the example below

        papis explore arxiv -a '"John Smith"' pick

    """
    import papis.arxiv
    logger = logging.getLogger('explore:arxiv')
    logger.info('Looking up...')
    data = papis.arxiv.get_data(
        query=query,
        author=author,
        title=title,
        abstract=abstract,
        comment=comment,
        journal=journal,
        report_number=report_number,
        category=category,
        id_list=id_list,
        page=page or 0,
        max_results=max
    )
    docs = [papis.document.from_data(data=d) for d in data]
    ctx.obj['documents'] += docs
    logger.info('{} documents found'.format(len(docs)))


@cli.command('libgen')
@click.pass_context
@click.help_option('--help', '-h')
@click.option('--author', '-a', default=None)
@click.option('--title', '-t', default=None)
@click.option('--isbn', '-i', default=None)
def libgen(ctx, author, title, isbn):
    """
    Look for documents on library genesis

    Examples of its usage are

    papis explore libgen -a 'Albert einstein' export --yaml einstein.yaml

    """
    from pylibgen import Library
    logger = logging.getLogger('explore:libgen')
    logger.info('Looking up...')
    lg = Library()
    ids = []

    if author:
        ids += lg.search(ascii(author), 'author')
    if isbn:
        ids += lg.search(ascii(isbn), 'isbn')
    if title:
        ids += lg.search(ascii(title), 'title')

    try:
        data = lg.lookup(ids)
    except:
        data = []

    docs = [papis.document.from_data(data=d.__dict__) for d in data]
    ctx.obj['documents'] += docs
    logger.info('{} documents found'.format(len(docs)))


@cli.command('crossref')
@click.pass_context
@click.help_option('--help', '-h')
@click.option('--query', '-q', default=None)
@click.option('--author', '-a', default=None)
@click.option('--title', '-t', default=None)
@click.option('--max', '-m', default=20)
def crossref(ctx, query, author, title, max):
    """
    Look for documents on crossref.org.

    Examples of its usage are

    papis explore crossref -a 'Albert einstein' pick export --bibtex lib.bib

    """
    logger = logging.getLogger('explore:crossref')
    logger.info('Looking up...')
    data = papis.crossref.get_data(
        query=query,
        author=author,
        title=title,
        max_results=max
    )
    docs = [papis.document.from_data(data=d) for d in data]
    ctx.obj['documents'] += docs
    logger.info('{} documents found'.format(len(docs)))


@cli.command('isbnplus')
@click.pass_context
@click.help_option('--help', '-h')
@click.option('--query', '-q', default=None)
@click.option('--author', '-a', default=None)
@click.option('--title', '-t', default=None)
def isbnplus(ctx, query, author, title):
    """
    Look for documents on isbnplus.com

    Examples of its usage are

    papis explore isbnplus -q 'Albert einstein' pick cmd 'firefox {doc[url]}'

    """
    from papis.isbnplus import get_data
    logger = logging.getLogger('explore:isbnplus')
    logger.info('Looking up...')
    try:
        data = get_data(
            query=query,
            author=author,
            title=title
        )
    except:
        data = []
    docs = [papis.document.from_data(data=d) for d in data]
    ctx.obj['documents'] += docs
    logger.info('{} documents found'.format(len(docs)))


@cli.command('isbn')
@click.pass_context
@click.help_option('--help', '-h')
@click.option('--query', '-q', default=None)
@click.option(
    '--service',
    '-s',
    default='goob',
    type=click.Choice(['wcat', 'goob', 'openl'])
)
def isbn(ctx, query, service):
    """
    Look for documents using isbnlib

    Examples of its usage are

    papis explore isbn -q 'Albert einstein' pick cmd 'firefox {doc[url]}'

    """
    from papis.isbn import get_data
    logger = logging.getLogger('explore:isbn')
    logger.info('Looking up...')
    data = get_data(
        query=query,
        service=service,
    )
    docs = [papis.document.from_data(data=d) for d in data]
    logger.info('{} documents found'.format(len(docs)))
    ctx.obj['documents'] += docs


@cli.command('dissemin')
@click.pass_context
@click.help_option('--help', '-h')
@click.option('--query', '-q', default=None)
def dissemin(ctx, query):
    """
    Look for documents on dissem.in

    Examples of its usage are

    papis explore dissemin -q 'Albert einstein' pick cmd 'firefox {doc[url]}'

    """
    import papis.dissemin
    logger = logging.getLogger('explore:dissemin')
    logger.info('Looking up...')
    data = papis.dissemin.get_data(query=query)
    docs = [papis.document.from_data(data=d) for d in data]
    ctx.obj['documents'] += docs
    logger.info('{} documents found'.format(len(docs)))


@cli.command('base')
@click.pass_context
@click.help_option('--help', '-h')
@click.option('--query', '-q', default=None)
def base(ctx, query):
    """
    Look for documents on the BielefeldAcademicSearchEngine

    Examples of its usage are

    papis explore base -q 'Albert einstein' pick cmd 'firefox {doc[url]}'

    """
    import papis.base
    logger = logging.getLogger('explore:base')
    logger.info('Looking up...')
    data = papis.base.get_data(query=query)
    docs = [papis.document.from_data(data=d) for d in data]
    ctx.obj['documents'] += docs
    logger.info('{} documents found'.format(len(docs)))


@cli.command('lib')
@click.pass_context
@click.help_option('--help', '-h')
@papis.cli.query_option()
@papis.cli.doc_folder_option()
@click.option('--library', '-l', default=None, help='Papis library to look')
def lib(ctx, query, doc_folder, library):
    """
    Query for documents in your library

    Examples of its usage are

        papis lib -l books einstein pick

    """
    logger = logging.getLogger('explore:lib')
    if doc_folder:
        ctx.obj['documents'] += [papis.document.from_folder(doc_folder)]
    db = papis.database.get(library=library)
    docs = db.query(query)
    logger.info('{} documents found'.format(len(docs)))
    ctx.obj['documents'] += docs
    assert(isinstance(ctx.obj['documents'], list))


@cli.command('pick')
@click.pass_context
@click.help_option('--help', '-h')
@click.option(
    '--number', '-n',
    type=int,
    default=None,
    help='Pick automatically the n-th document'
)
def pick(ctx, number):
    """
    Pick a document from the retrieved documents

    Examples of its usage are

    papis explore bibtex lib.bib pick

    """
    docs = ctx.obj['documents']
    if number is not None:
        docs = [docs[number - 1]]
    ctx.obj['documents'] = list(filter(
        lambda x: x is not None,
        [papis.api.pick_doc(docs)]
    ))
    assert(isinstance(ctx.obj['documents'], list))


@cli.command('bibtex')
@click.pass_context
@click.argument('bibfile', type=click.Path(exists=True))
@click.help_option('--help', '-h')
def bibtex(ctx, bibfile):
    """
    Import documents from a bibtex file

    Examples of its usage are

    papis explore bibtex lib.bib pick

    """
    logger = logging.getLogger('explore:bibtex')
    logger.info('Reading in bibtex file {}'.format(bibfile))
    docs = [
        papis.document.from_data(d)
        for d in papis.bibtex.bibtex_to_dict(bibfile)
    ]
    ctx.obj['documents'] += docs
    logger.info('{} documents found'.format(len(docs)))


@cli.command('citations')
@click.pass_context
@papis.cli.query_option()
@papis.cli.doc_folder_option()
@click.help_option('--help', '-h')
@click.option(
    "--save", "-s",
    is_flag=True,
    default=False,
    help="Store the citations in the document's folder for later use"
)
@click.option(
    "--rmfile",
    is_flag=True,
    default=False,
    help="Remove the stored citations file"
)
@click.option(
    "--max-citations", "-m", default=-1,
    help='Number of citations to be retrieved'
)
def citations(ctx, query, doc_folder, max_citations, save, rmfile):
    """
    Query the citations of a paper

    Example:

    Go through the citations of a paper and export it in a yaml file

        papis explore citations 'einstein' export --yaml einstein.yaml

    """
    from prompt_toolkit.shortcuts import ProgressBar
    logger = logging.getLogger('explore:citations')

    if doc_folder is not None:
        documents = [papis.document.from_folder(doc_folder)]
    else:
        documents = papis.api.get_documents_in_lib(
            papis.config.get_lib_name(),
            search=query
        )

    if not documents:
        logger.warning(papis.strings.no_documents_retrieved_message)
        return

    doc = papis.api.pick_doc(documents)
    db = papis.database.get()
    citations_file = os.path.join(doc.get_main_folder(), 'citations.yaml')

    if os.path.exists(citations_file):
        if rmfile:
            logger.info('Removing {0}'.format(citations_file))
            os.remove(citations_file)
        else:
            logger.info(
                'A citations file exists in {0}'.format(citations_file)
            )
            if papis.utils.confirm('Do you want to use it?'):
                yaml.callback(citations_file)
                return

    if not doc.has('citations') or doc['citations'] == []:
        logger.warning('No citations found')
        return

    dois = [d.get('doi') for d in doc['citations'] if d.get('doi')]
    if max_citations < 0:
        max_citations = len(dois)
    dois = dois[0:min(max_citations, len(dois))]

    logger.info("%s citations found" % len(dois))
    logger.info("Fetching {} citations'".format(max_citations))
    dois_with_data = []
    failed_dois = []

    with ProgressBar() as progress:
        progress.bottom_toolbar = (
            'Getting {0} doi information'.format(len(dois))
        )
        for j, doi in progress(enumerate(dois), total=len(dois)):
            citation = db.query_dict(dict(doi=doi))

            if citation:
                progress.bottom_toolbar = [
                    ('fg:green', 'Found in library'),
                    ('', ' doi: {doi}'.format(doi=doi))
                ]
                dois_with_data.append(citation[0])
            else:
                try:
                    dois_with_data.append(
                        papis.crossref.doi_to_data(doi)
                    )
                except ValueError:
                    progress.bottom_toolbar = [
                        ('fg:ansired', 'Error resolving doi'),
                        ('', ' doi: {doi}'.format(doi=doi))
                    ]
                    failed_dois.append(doi)
                except Exception as e:
                    progress.bottom_toolbar = [
                        ('fg:ansired', str(e)),
                        ('', ' doi: {doi}'.format(doi=doi))
                    ]
                else:
                    progress.bottom_toolbar = 'doi: {doi}'.format(doi=doi)

    if failed_dois:
        logger.error('Dois not found:')
        for doi in failed_dois:
            logger.error(doi)

    docs = [papis.document.Document(data=d) for d in dois_with_data]
    if save:
        logger.info('Storing citations in "{0}"'.format(citations_file))
        with open(citations_file, 'a+') as fd:
            logger.info(
                "Writing {} documents' yaml into {}".format(
                    len(docs),
                    citations_file
                )
            )
            yamldata = papis.commands.export.run(docs, to_format='yaml')
            fd.write(yamldata)
    ctx.obj['documents'] += docs


@cli.command('yaml')
@click.pass_context
@click.argument('yamlfile', type=click.Path(exists=True))
@click.help_option('--help', '-h')
def yaml(ctx, yamlfile):
    """
    Import documents from a yaml file

    Examples of its usage are

    papis explore yaml lib.yaml pick

    """
    import yaml
    logger = logging.getLogger('explore:yaml')
    logger.info('Reading in yaml file {}'.format(yamlfile))
    docs = [
        papis.document.from_data(d) for d in yaml.load_all(open(yamlfile))
    ]
    ctx.obj['documents'] += docs
    logger.info('{} documents found'.format(len(docs)))


@cli.command('json')
@click.pass_context
@click.argument('jsonfile', type=click.Path(exists=True))
@click.help_option('--help', '-h')
def json(ctx, jsonfile):
    """
    Import documents from a json file

    Examples of its usage are

    papis explore json lib.json pick

    """
    import json
    logger = logging.getLogger('explore:json')
    logger.info('Reading in json file {}'.format(jsonfile))
    docs = [
        papis.document.from_data(d) for d in json.load(open(jsonfile))
    ]
    ctx.obj['documents'] += docs
    logger.info('{} documents found'.format(len(docs)))


@cli.command('export')
@click.pass_context
@click.help_option('--help', '-h')
@click.option(
    "-f",
    "--format",
    help="Format for the document",
    type=click.Choice(papis.commands.export.available_formats()),
    default="bibtex",
)
@click.option(
    "-o",
    "--out",
    help="Outfile to write information to",
    type=click.Path(),
    default=None,
)
def export(ctx, format, out):
    """
    Export retrieved documents into various formats for later use

    Examples of its usage are

    papis explore crossref -m 200 -a 'Schrodinger' export --yaml lib.yaml

    """
    logger = logging.getLogger('explore:yaml')
    docs = ctx.obj['documents']

    outstring = papis.commands.export.run(docs, to_format=format)
    if out is not None:
        with open(out, 'a+') as fd:
            logger.info(
                "Writing {} documents' in {} into {}".format(
                    len(docs),
                    format,
                    out
                )
            )
            fd.write(outstring)
    else:
        print(outstring)


@cli.command('cmd')
@click.pass_context
@click.help_option('--help', '-h')
@click.argument('command', type=str)
def cmd(ctx, command):
    """
    Run a general command on the document list

    Examples of its usage are:

    Look for 200 Schroedinger papers, pick one, and add it via papis-scihub

    papis explore crossref -m 200 -a 'Schrodinger' \\
        pick cmd 'papis scihub {doc[doi]}'

    """
    from subprocess import call
    import shlex
    logger = logging.getLogger('explore:cmd')
    docs = ctx.obj['documents']
    for doc in docs:
        fcommand = papis.utils.format_doc(command, doc)
        splitted_command = shlex.split(fcommand)
        logger.info('Calling %s' % splitted_command)
        call(splitted_command)
