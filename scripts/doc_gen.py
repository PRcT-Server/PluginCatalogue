import os
import re
import shutil
from contextlib import contextmanager
from typing import List, IO, Iterable

import constants
import utils
from label import get_label_set
from plugin import get_plugin_list, Plugin
from translation import Text, get_language, get_file_name, LANGUAGES, with_language


def get_plugin_detail_link(plugin_id: str):
	return '/plugins/{}/{}'.format(plugin_id, get_file_name('readme.md'))


def get_label_doc_link(label_id: str):
	return '/labels/{}/{}'.format(label_id, get_file_name('readme.md'))


def get_root_readme_file_path():
	return os.path.join(constants.CATALOGUE_FOLDER, get_file_name('readme.md'))


def get_full_index_file_path():
	return os.path.join(constants.CATALOGUE_FOLDER, get_file_name('full.md'))


def get_label_list_markdown(plugin: Plugin):
	return ', '.join(map(lambda l: '[`{}`]({})'.format(l, get_label_doc_link(l.id)), plugin.labels))


def write_translation_nav(file_name: str, file: IO[str]):
	nav_list = []
	for lang in LANGUAGES:
		with with_language(lang):
			lang_name = Text('_language_name').get()
		if lang == get_language():
			text = '**{}**'.format(lang_name)
		else:
			with with_language(lang):
				text = '[{}]({})'.format(lang_name, get_file_name(file_name))
		nav_list.append('{}'.format(text))
	file.write('{}\n'.format(' | '.join(nav_list)))
	file.write('\n')


def write_back_to_index_nav(file: IO[str]):
	file.write('{} [{}]({})\n'.format(utils.format_markdown('>>>'), Text('back_to_index'), get_file_name('/readme.md')))
	file.write('\n')


@contextmanager
def write_nav(file_path: str):
	with utils.write_file(file_path) as file:
		write_translation_nav(os.path.basename(file_path), file)
		write_back_to_index_nav(file)
		yield file


def write_label_info(file: IO[str]):
	label_set = get_label_set()
	file.write('## {}\n'.format(Text('label_index')))
	file.write('\n')
	for label in label_set.get_label_list():
		file.write('- [{}]({})\n'.format(label, get_label_doc_link(label.id)))
	file.write('\n')


def generate_index(plugin_list: Iterable[Plugin], file: IO[str]):
	plugin_list = list(plugin_list)
	file.write('{}: {}\n'.format(Text('plugin_amount'), len(plugin_list)))
	file.write('\n')
	table = Table(Text('plugin_name'), Text('authors'), Text('summary'), Text('labels'))
	for plugin in plugin_list:
		table.add_row(
			'[{}]({})'.format(plugin.name, get_plugin_detail_link(plugin.id)),
			', '.join(map(lambda a: a.to_markdown(), plugin.authors)),
			plugin.summary,
			get_label_list_markdown(plugin)
		)
	table.write(file)


def write_plugin(plugin: Plugin, file: IO[str]):
	file.write('## {}\n'.format(plugin.id))
	file.write('\n')

	file.write('- {}: `{}`\n'.format(Text('plugin_id'), plugin.id))
	file.write('- {}: {}\n'.format(Text('plugin_name'), plugin.name))

	if plugin.is_data_fetched():
		file.write('- {}: {}\n'.format(Text('version'), plugin.latest_version))
		file.write('  - {}: {}\n'.format(Text('metadata_version'), plugin.meta_info.version))
		file.write('  - {}: {}\n'.format(Text('release_version'), plugin.release_summary.latest_version))
	else:
		file.write('- {}: *{}*\n'.format(Text('version'), Text('data_fetched_failed')))

	file.write('- {}: {}\n'.format(Text('authors'), ', '.join(map(lambda a: a.to_markdown(), plugin.authors))))
	file.write('- {}: {}\n'.format(Text('repository'), plugin.repository))
	file.write('- {}: {}\n'.format(Text('labels'), get_label_list_markdown(plugin)))
	file.write('- {}: {}\n'.format(Text('summary'), plugin.summary))

	if plugin.is_data_fetched():
		if len(plugin.meta_info.dependencies) > 0:
			file.write('- {}:\n'.format(Text('dependencies')))
			file.write('\n')
			table = Table(Text('plugin_id'), Text('dependencies.requirement'))
			for pid, req in plugin.meta_info.dependencies.items():
				table.add_row(
					'[{}](https://pypi.org/project/{}/)'.format(pid, get_plugin_detail_link(pid)),
					utils.format_markdown(req)
				)
			table.write(file)
		else:
			file.write('- {}: {}\n'.format(Text('dependencies'), Text('none')))
	else:
		file.write('- {}: *{}*\n'.format(Text('dependencies'), Text('data_fetched_failed')))

	if plugin.is_data_fetched():
		if len(plugin.meta_info.requirements) > 0:
			file.write('- {}:\n'.format(Text('requirements')))
			file.write('\n')
			table = Table(Text('python_package'), Text('requirements.requirement'))
			for line in plugin.meta_info.requirements:
				package = re.match(r'^[A-Za-z.-]+', line).group()
				req = utils.remove_prefix(line, package)
				table.add_row(
					'[{}](https://pypi.org/project/{}/)'.format(package, package),
					utils.format_markdown(req)
				)
			table.write(file)
		else:
			file.write('- {}: {}\n'.format(Text('requirements'), Text('none')))
	else:
		file.write('- {}: *{}*\n'.format(Text('requirements'), Text('data_fetched_failed')))
	file.write('\n')

	file.write('**{}**\n'.format(Text('description')))
	file.write('\n')
	file.write(plugin.readme.get())
	file.write('\n')


def generate_full(plugin_list: Iterable[Plugin], file: IO[str]):
	with utils.read_file(os.path.join(constants.TEMPLATE_FOLDER, get_file_name('full_header.md'))) as header:
		file.write(header.read())
	file.write('\n')
	for plugin in plugin_list:
		write_plugin(plugin, file)


def generate_labels(plugin_list: List[Plugin]):
	label_root = os.path.join(constants.CATALOGUE_FOLDER, 'labels')
	for label in get_label_set().get_label_list():
		with write_nav(os.path.join(label_root, label.id, get_file_name('readme.md'))) as file:
			file.write('# {}\n'.format(label))
			file.write('\n')
			file.write('{}\n'.format(Text('plugin_index_with_label')).format(label))
			file.write('\n')
			generate_index(filter(lambda plg: label in plg.labels, plugin_list), file)


def generate_plugins(plugin_list: List[Plugin]):
	plugin_root = os.path.join(constants.CATALOGUE_FOLDER, 'plugins')
	for plugin in plugin_list:
		with write_nav(os.path.join(plugin_root, plugin.id, get_file_name('readme.md'))) as file:
			write_plugin(plugin, file)


def generate_doc():
	print('Generating doc')
	plugin_list = get_plugin_list()
	plugin_list.fetch_data(fail_hard=False)
	if os.path.isdir(constants.CATALOGUE_FOLDER):
		shutil.rmtree(constants.CATALOGUE_FOLDER)
	os.mkdir(constants.CATALOGUE_FOLDER)

	def write_doc():
		with write_nav(get_root_readme_file_path()) as file:
			with utils.read_file(os.path.join(constants.TEMPLATE_FOLDER, get_file_name('index_header.md'))) as header:
				file.write(header.read())
			file.write('\n')
			write_label_info(file)
			file.write('-------\n\n')
			generate_index(plugin_list, file)

		generate_labels(plugin_list)
		generate_plugins(plugin_list)

		with write_nav(get_full_index_file_path()) as file:
			generate_full(plugin_list, file)

	for lang in LANGUAGES:
		print('Generating doc in language {}'.format(lang))
		with with_language(lang):
			write_doc()


class Table:
	def __init__(self, *title):
		self.__title = title
		self.__column_count = len(title)
		self.__rows: List[tuple] = []

	def add_row(self, *items):
		assert len(items) == self.__column_count
		self.__rows.append(items)

	@staticmethod
	def __write_row(file: IO[str], items: tuple):
		file.write('| {} |\n'.format(' | '.join(map(str, items))))

	def write(self, file: IO[str]):
		self.__write_row(file, self.__title)
		self.__write_row(file, ('---', ) * self.__column_count)
		for row in self.__rows:
			self.__write_row(file, row)
		file.write('\n')
