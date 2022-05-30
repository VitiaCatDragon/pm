# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'password_box.ui'
#
# Created by: PyQt5 UI code generator 5.14.1
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(400, 70)
        self.widget = QtWidgets.QWidget(Dialog)
        self.widget.setGeometry(QtCore.QRect(0, 10, 391, 56))
        self.widget.setObjectName("widget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.widget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.password = QtWidgets.QLineEdit(self.widget)
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.password.setObjectName("password")
        self.verticalLayout.addWidget(self.password)
        self.actions = QtWidgets.QDialogButtonBox(self.widget)
        self.actions.setOrientation(QtCore.Qt.Horizontal)
        self.actions.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.actions.setObjectName("actions")
        self.verticalLayout.addWidget(self.actions)

        self.retranslateUi(Dialog)
        self.actions.accepted.connect(Dialog.accept)
        self.actions.rejected.connect(Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        self.password.setPlaceholderText(_translate("Dialog", "Пароль root-пользователя"))
