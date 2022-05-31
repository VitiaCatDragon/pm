import dataclasses
import json
import os
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QThread, QObject

import password_box
from main_window import Ui_MainWindow

import subprocess
import sys


@dataclasses.dataclass
class Package:
    name: str
    version: str
    description: str
    url: str
    author: str
    license: str


class CacheManager:

    def __init__(self):
        self.cache_file = "cache.json"
        self.cache = {'pypi': {}, 'npm': {}}
        if not os.path.isfile(self.cache_file):
            self.save()
        else:
            with open("cache.json", "r") as f:
                self.cache = json.load(f)

    def get(self, manager, package_name):
        return Package(**self.cache[manager][package_name])

    def has_package(self, manager, package_name):
        return package_name in self.cache[manager]

    def add_package(self, manager, package):
        self.cache[manager][package.name] = dataclasses.asdict(package)
        self.save()

    def remove_package(self, manager, package_name):
        del self.cache[manager][package_name]
        self.save()

    def save(self):
        with open("cache.json", "w") as f:
            json.dump(self.cache, f, indent=4)


class PyPi(QObject):
    PASSWORD_NEEDED = True
    fetch_signal = QtCore.pyqtSignal(int)
    name = 'pypi'

    def __init__(self, cache, parent=None):
        super(PyPi, self).__init__(parent)
        self._cache = cache

    def fetch(self, outdated=False):
        packages = []
        # get output from the command
        output = subprocess.check_output(
            ["pip3", "list", "--format=json", "--outdated" if outdated else ""])
        # decode the output
        output = output.decode("utf-8")
        j = json.loads(output)
        i = 1
        for package in j:
            if self._cache.has_package(self.name, package["name"]):
                if package['version'] != self._cache.get(self.name, package["name"]).version:
                    p = self.info(package["name"])
                    self._cache.add_package(self.name, p)
                    if outdated:
                        p.version += f" -> {package['latest_version']}"
                    packages.append(p)
                else:
                    p = self._cache.get(self.name, package["name"])
                    if outdated:
                        p.version += f" -> {package['latest_version']}"
                    packages.append(p)
            else:
                p = self.info(package["name"])
                self._cache.add_package(self.name, p)
                packages.append(p)
            self.fetch_signal.emit(int(i / len(j) * 100))
            i += 1
        return packages

    def info(self, package):
        output = subprocess.check_output(["pip3", "show", package])
        output = output.decode("utf-8")
        name, version, description, url, author, _license = "", "", "", "", "", ""
        for line in output.splitlines():
            if line.startswith("Name:"):
                name = line.split(":")[1].strip()
            elif line.startswith("Version:"):
                version = line.split(":")[1].strip()
            elif line.startswith("Summary:"):
                description = line.split(":")[1].strip()
            elif line.startswith("Home-page:"):
                url = ':'.join(line.split(":")[1:]).strip()
            elif line.startswith("Author:"):
                author = line.split(":")[1].strip()
            elif line.startswith("License:"):
                _license = line.split(":")[1].strip()
        return Package(name, version, description, url, author, _license)

    def uninstall(self, package, password):
        subprocess.call(["pip3", "uninstall", "-y", package])
        return True

    def update(self, package, password):
        subprocess.call(["pip3", "install", "-U", package])
        return True


class NPM(QtCore.QObject):
    PASSWORD_NEEDED = True
    fetch_signal = QtCore.pyqtSignal(int)
    name = 'npm'

    def __init__(self, cache, parent=None):
        super().__init__(parent)
        self._cache = cache

    def fetch(self, outdated=False):
        packages = []
        # get output from the command
        if outdated:
            try:
                output = subprocess.check_output(["npm", "outdated", "--json", "--location=global"],
                                                 stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:  # npm returning exit code 1, bug in npm
                output = e.output
        else:
            output = subprocess.check_output(["npm", "list", "--json", "--location=global"])
        # decode the output
        output = output.decode("utf-8")
        j = json.loads(output)
        i = 0
        for package in j['dependencies'] if not outdated else j:
            if self._cache.has_package(self.name, package):
                # if package['version'] != self._cache.get(self.name, package).version:
                #     p = self.info(package, j['dependencies'][package]['version'])
                #     self._cache.add_package(self.name, p)
                #     packages.append(p)
                # else:
                p = self._cache.get(self.name, package)
                if outdated:
                    p.version += f" -> {j[package]['latest']}"
                packages.append(p)
            else:
                p = self.info(package, j['dependencies'][package]['version'] if not outdated else j[package]['current'])
                self._cache.add_package(self.name, p)
                if outdated:
                    p.version += f" -> {j[package]['latest']}"
                packages.append(p)
            self.fetch_signal.emit(int(i / len(j) * 100))
            i += 1
        return packages

    def info(self, package, version):
        output = subprocess.check_output(["npm", "show", package, "--json"])
        output = output.decode("utf-8")
        output = json.loads(output)
        return Package(output['name'], version, output['description'] if 'description' in output else 'None',
                       output['homepage'] if 'homepage' in output else 'None',
                       output['author'] if 'author' in output else 'None',
                       output['license'])

    def uninstall(self, package, password):
        p = subprocess.Popen(['sudo', '-S', "npm", "uninstall", "-y", "--location=global", package],
                             stderr=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stdin=subprocess.PIPE)
        out, err = p.communicate((password + '\n').encode('utf-8'))
        print(out.decode('utf-8'), err.decode('utf-8'))
        if not out:
            return False
        else:
            return True

    def update(self, package, password):
        p = subprocess.Popen(["sudo", "-S", "npm", "update", package, "--location=global"], stderr=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stdin=subprocess.PIPE)
        out, err = p.communicate((password + '\n').encode('utf-8'))
        print(out.decode('utf-8'), err.decode('utf-8'))
        if not out:
            return False
        else:
            return True


def is_installed(pm):
    try:
        subprocess.check_output([pm, "--version"])
    except FileNotFoundError:
        return False
    except Exception as e:
        print(e)
        return False
    return True


class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super(Ui, self).__init__()  # Call the inherited classes __init__ method
        Ui_MainWindow().setupUi(self)
        self.packages_list = self.findChild(QtWidgets.QTableWidget, 'packages')
        self.show()
        self.t = None
        self.progress = QtWidgets.QProgressBar(self)
        self.progress.setGeometry(QtCore.QRect(10, 10, 200, 25))
        self.progress.setValue(0)
        self.progress.hide()
        self.status_label = QtWidgets.QLabel(self)
        self.status_label.setGeometry(QtCore.QRect(10, 10, 200, 25))
        self.status_label.hide()

        header = self.packages_list.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.Stretch)

        self.cache = CacheManager()
        self.package_manager = None

        self.packages_list.customContextMenuRequested.connect(self.show_context_menu)

        self.statusBar().addWidget(self.progress)
        self.statusBar().addWidget(self.status_label)

        self.pip_action = self.findChild(QtWidgets.QAction, 'pip')
        self.npm_action = self.findChild(QtWidgets.QAction, 'npm')

        pm = {'pip3': is_installed('pip3'), 'npm': is_installed('npm')}
        self.pip_action.setEnabled(pm['pip3'])
        self.npm_action.setEnabled(pm['npm'])
        self.pm = [k for k, v in pm.items() if v]
        if len(pm) == 0:
            QtWidgets.QMessageBox.critical(self, 'Ошибка', 'Ни один пакетный менеджер не установлен (pip3, npm)')
            self.close()
            return

        self.pip_action.triggered.connect(lambda x: self.update_package_manager('pip3'))
        self.npm_action.triggered.connect(lambda x: self.update_package_manager('npm'))

        self.all_packages = self.findChild(QtWidgets.QAction, 'all_packages')
        self.outdated_packages = self.findChild(QtWidgets.QAction, 'outdated_packages')
        self.all_packages.triggered.connect(lambda: self.update_view_type('all'))
        self.outdated_packages.triggered.connect(lambda: self.update_view_type('outdated'))

        self.show_outdated = False
        self.is_updating = False

        self.update_package_manager(self.pm[0])

    class FetchThread(QThread):

        progress_signal = QtCore.pyqtSignal(int)

        def __init__(self, parent):
            super().__init__()
            self.parent = parent

        def run(self):
            self.parent.packages_list.clearContents()
            self.parent.packages_list.setRowCount(0)
            packages = self.parent.package_manager.fetch(self.parent.show_outdated)
            i = 0
            for package in packages:
                self.parent.packages_list.insertRow(self.parent.packages_list.rowCount())
                count_ = self.parent.packages_list.rowCount() - 1
                self.parent.packages_list.setItem(count_, 0,
                                                  QtWidgets.QTableWidgetItem(package.name))
                self.parent.packages_list.setItem(count_, 1,
                                                  QtWidgets.QTableWidgetItem(package.version))
                self.parent.packages_list.setItem(count_, 2,
                                                  QtWidgets.QTableWidgetItem(package.description))
                self.parent.packages_list.setItem(count_, 3,
                                                  QtWidgets.QTableWidgetItem(package.url))
                self.parent.packages_list.setItem(count_, 4,
                                                  QtWidgets.QTableWidgetItem(package.author))
                self.parent.packages_list.setItem(count_, 5,
                                                  QtWidgets.QTableWidgetItem(package.license))
                i += 1
                self.progress_signal.emit(int(i / len(packages) * 100))

    def update_list(self):
        if self.t is not None and not self.t.isFinished():
            self.t.terminate()
        self.status_label.setText('Получаем список пакетов...')
        self.progress.setValue(0)
        self.is_updating = True
        self.progress.show()
        self.status_label.show()
        self.t = Ui.FetchThread(self)
        self.t.progress_signal.connect(self.progress.setValue)
        self.t.finished.connect(self.update_finished)
        self.t.start()

    def update_finished(self):
        self.is_updating = False
        self.progress.hide()
        self.status_label.hide()

    def show_context_menu(self, position):
        menu = QtWidgets.QMenu()
        update = menu.addAction("Обновить список")
        update_in_cache = menu.addAction("Обновить кэш пакета(ов)")
        update_package = menu.addAction("Обновить пакет(ы)")
        uninstall = menu.addAction("Удалить пакет(ы)")
        if len(self.packages_list.selectedItems()) == 0:
            uninstall.setEnabled(False)
            update_in_cache.setEnabled(False)
            update_package.setEnabled(False)
        if self.is_updating:
            update.setEnabled(False)
        action = menu.exec(self.packages_list.mapToGlobal(position))
        if action == update:
            self.update_list()
        elif action == uninstall:
            self.uninstall_package()
        elif action == update_in_cache:
            for index in self.packages_list.selectionModel().selectedRows():
                package = self.packages_list.item(index.row(), 0).text()
                self.cache.remove_package(self.package_manager.name, package)
            self.update_list()
        elif action == update_package:
            self.update_package()

    def uninstall_package(self):
        if self.package_manager.name in ['npm']:
            password = QtWidgets.QDialog()
            password_box.Ui_Dialog().setupUi(password)
            password.exec()
            password = password.findChild(QtWidgets.QLineEdit, 'password').text()
        else:
            password = ''
        for index in self.packages_list.selectionModel().selectedRows():
            package = self.packages_list.item(index.row(), 0).text()
            if self.package_manager.uninstall(package, password):
                self.cache.remove_package(self.package_manager.name, package)
                self.statusBar().showMessage(f"Пакет {package} успешно удален")
                self.packages_list.removeRow(self.packages_list.currentRow())
            else:
                self.statusBar().showMessage(f"Ошибка удаления! Возможно, Вы ввели неверный пароль.")
        self.update_list()

    def update_package(self):
        if self.package_manager.name in ['npm']:
            password = QtWidgets.QDialog()
            password_box.Ui_Dialog().setupUi(password)
            password.exec()
            password = password.findChild(QtWidgets.QLineEdit, 'password').text()
        else:
            password = ''
        packages = []
        for index in self.packages_list.selectionModel().selectedRows():
            package = self.packages_list.item(index.row(), 0).text()
            self.package_manager.update(package, password)
            packages.append(package)
        self.update_list()
        self.statusBar().showMessage(f"Пакет(ы) {','.join(packages)} успешно обновлен(ы)")

    def update_package_manager(self, package_manager):
        if self.package_manager is not None:
            self.package_manager.fetch_signal.disconnect()
        if package_manager == 'pip3':
            if 'npm' in self.pm:
                self.npm_action.setEnabled(True)
            self.npm_action.setChecked(False)
            self.pip_action.setEnabled(False)
            self.pip_action.setChecked(True)
            self.package_manager = PyPi(self.cache)
        elif package_manager == 'npm':
            if 'pip3' in self.pm:
                self.pip_action.setEnabled(True)
            self.pip_action.setChecked(False)
            self.npm_action.setEnabled(False)
            self.npm_action.setChecked(True)
            self.package_manager = NPM(self.cache)

        self.package_manager.fetch_signal.connect(self.progress.setValue)
        self.update_list()

    def update_view_type(self, view_type):
        if view_type == 'all':
            self.all_packages.setChecked(True)
            self.outdated_packages.setChecked(False)
            self.all_packages.setEnabled(False)
            self.outdated_packages.setEnabled(True)
            self.show_outdated = False
            self.update_list()
        elif view_type == 'outdated':
            self.all_packages.setChecked(False)
            self.outdated_packages.setChecked(True)
            self.all_packages.setEnabled(True)
            self.outdated_packages.setEnabled(False)
            self.show_outdated = True
            self.update_list()


app = QtWidgets.QApplication(sys.argv)
window = Ui()
app.exec()
