from sublime_db.core.typecheck import List, Optional, Generator, Any, Callable, Dict

import os
import shutil
import zipfile
import gzip
import urllib.request
import sublime
import json
from sublime_db import core

def _adapters_path() -> str:
	return os.path.join(sublime.packages_path() ,"sublime_db/debug_adapters")

class AdapterConfiguration:
	class Installation:
		def __init__(self, name: str, url: str, format: str) -> None:
			self.name = name
			self.url = url
			self.format = format

		@staticmethod
		def from_json(json: dict) -> 'AdapterConfiguration.Installation':
			return AdapterConfiguration.Installation(json['name'], json['url'], json['format'])

	def __init__(self, type: str, command: List[str], tcp_port: Optional[int], tcp_address: Optional[str], vscode_package_file: Optional[str], installation: Optional['AdapterConfiguration.Installation']) -> None:
		self.type = type
		self.command = command
		self.tcp_port = tcp_port
		self.tcp_address = tcp_address
		self.vscode_package_file = vscode_package_file
		self.snippets = [] #type: List[dict]
		self.installation = installation
		self.installed = True			
		self.load_installation_if_needed()
		
	def load_installation_if_needed (self) -> None:
		if not self.installation:
			return

		self.installed = os.path.isdir(os.path.join(_adapters_path(), self.installation.name))
		snippets_file = os.path.join(os.path.join(_adapters_path(), self.installation.name, 'snippets.json'))
		try:
			with open(snippets_file) as file:
				self.snippets = json.load(file)
		except Exception as e:
			print('No snippets loaded. {}'.format(e))

	@staticmethod
	def from_json(type: str, json: dict, window: sublime.Window) -> 'AdapterConfiguration':
		variables = window.extract_variables()
		command = sublime.expand_variables(json['command'], variables) 
		vscode_package_file = json.get('vscode-package-file')
		if vscode_package_file:
			vscode_package_file = sublime.expand_variables(vscode_package_file, variables)

		sublime.expand_variables(json['command'], variables)
		install_json = json.get('installation')
		installation = None
		if install_json:
			installation = AdapterConfiguration.Installation.from_json(install_json)
		r = AdapterConfiguration(
			type, 
			command,
			json.get('tcp_port'),
			json.get('tcp_address'),
			vscode_package_file,
			installation
		)
		return r

@core.async
def install_adapter(adapter: AdapterConfiguration) -> core.awaitable[None]:
	assert adapter.installation
	yield from core.main_loop.run_in_executor(core.main_executor, _install_adapter_blocking, adapter)

	vscode_package_file = os.path.join(_adapters_path(), adapter.installation.name, 'extension', 'package.json')
	snippets_output_file = os.path.join(_adapters_path(), adapter.installation.name, 'snippets.json')

	try:
		snippets = [] #type: List[dict]
		with open(vscode_package_file) as file:
			j = json.load(file)
			for debugger in j['contributes']['debuggers']:
				snippets.extend(debugger.get('configurationSnippets', []))
					
		with open(snippets_output_file, 'w') as file:
			content = json.dumps(snippets)

			# strip out unescaped stuff
			# FIXME this isn't correct... but good enough for now...
			content = content.replace('^\\\"', '')
			content = content.replace('\\\"', '')
			file.write(content)

		print ('snippets found: ', snippets)
	except Exception as e:
		print('Failed to find debug configuration snippets in vscode package.json file, ', str(e))

	adapter.load_installation_if_needed()

def _install_adapter_blocking(adapter: AdapterConfiguration):
	install_cfg = adapter.installation
	assert install_cfg, 'No install information for this adapter configuration'

	adapters_path = _adapters_path()
	adapter_name = install_cfg.name

	url = install_cfg.url
	archive_format = install_cfg.format

	if archive_format not in ["zip", "zip.gz"]:
		raise Exception("The archive extension is incorrect")

	adapter_path = os.path.join(adapters_path, adapter_name)

	if os.path.isdir(adapter_path):
		print("Adapter %s already exists, deleting folder" % (adapter_path,))
		shutil.rmtree(adapter_path, ignore_errors=True)

	request = urllib.request.Request(url, headers =  {
		"Accept-Encoding": "gzip"
	})

	response = urllib.request.urlopen(request)
	if response.getcode() != 200:
		raise Exception("Bad response from server, got code %d" % (response.getcode(),))
	os.mkdir(adapter_path)
	
	content_encoding = response.headers.get('Content-Encoding')
	if content_encoding == 'gzip':
		response = gzip.GzipFile(fileobj=response)

	archive_name = "%s.%s" % (adapter_path, archive_format)
	with open(archive_name, "wb") as out_file:
		shutil.copyfileobj(response, out_file)

	if archive_format == "zip":
		with zipfile.ZipFile(archive_name) as zf:
			zf.extractall(adapter_path)

	os.remove(archive_name)
