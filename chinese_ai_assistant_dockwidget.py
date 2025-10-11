# -*- coding: utf-8 -*-
"""
/***************************************************************************
                      Chinese AI Assistant Dock Widget
  A dock widget that provides a QGIS assistant, combining a LLM with the
  Phoenix-GIS knowledge database.
                              -------------------
        begin                : 2025-10-01
        copyright            : (C) 2025 by phoenix-gis
        email                : phoenixgis@sina.com
        website              : phoenix-gis.cn
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDockWidget, QGridLayout
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtGui import QTextCursor
from qgis.core import QgsSettings

from .stream_chat_worker import StreamChatWorker
from .chatbot_browser import ChatbotBrowser
from .setting_dialog import SettingDialog
from .global_defs import *
from .resources_rc import *

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'chinese_ai_assistant_dockwidget_base.ui'))

class ChineseAIAssistantDockWidget(QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self, iface, parent=None):
        """Constructor."""
        super(ChineseAIAssistantDockWidget, self).__init__(parent)
        self.iface = iface
        self.chat_worker = None
        self.setupUi(self)

        self.chatbot_browser = ChatbotBrowser(iface)

        chatbot_layout = QGridLayout()
        chatbot_layout.setContentsMargins(0, 0, 0, 0)
        chatbot_layout.addWidget(self.chatbot_browser)
        self.widgetChatbotParent.setLayout(chatbot_layout)

        self.btnSendOrTerminate.clicked.connect(self.handle_click_send_or_terminate_btn)
        self.btnClear.clicked.connect(self.handle_click_clear_btn)
        self.btnSetting.clicked.connect(self.handle_click_setting_btn)
        self.chatbot_browser.show_setting_dlg.connect(self.handle_click_setting_btn)

        # use custom function to deal with "Open Links".
        self.chatbot_browser.setOpenLinks(False)

        # 0: Send 1: Terminate
        self.btn_send_or_terminate_tag = 0

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def handle_click_send_or_terminate_btn(self):
        if self.btn_send_or_terminate_tag == 0:
            # add question in chatbot
            question_str = self.plainTextEdit.toPlainText()
            self.chatbot_browser.pre_process_markdown()
            self.chatbot_browser.append_markdown(self.tr("**Question:") + question_str + "**\n\n")
            self.chatbot_browser.append_markdown(self.tr("**Answer:") + "**\n\n")

            gSetting = QgsSettings()
            user_email = gSetting.value(USER_EMAIL_TAG)
            if not user_email:
                user_email = ""

            # repare request body.
            request_data = {
                "prompt": question_str,
                "history": [],
                "db_name": "QGIS",
                "similarity_threshold": 0.5,
                "chunk_cnt": 5,
                "email": user_email,
                "version": VERSION
            }

            self.chat_worker = StreamChatWorker(request_data)
            self.chat_worker.chunks_info_received.connect(self.on_chunks_info_received)
            self.chat_worker.content_received.connect(self.on_content_received)
            self.chat_worker.stream_ended.connect(self.on_stream_ended)
            self.chat_worker.error_occurred.connect(self.on_error_occurred)
            self.chat_worker.start()

            self.btn_send_or_terminate_tag = 1
            self.btnSendOrTerminate.setText(self.tr("Stop"))
        elif self.btn_send_or_terminate_tag == 1:
            if self.chat_worker:
                self.btnSendOrTerminate.setEnabled(False)
                self.chat_worker.exit()
                self.chat_worker.wait(3000)

            self.chatbot_browser.post_process_markdown()
            self.btnSendOrTerminate.setEnabled(True)
            self.btn_send_or_terminate_tag = 0
            self.btnSendOrTerminate.setText(self.tr("Send"))

    def handle_click_clear_btn(self):
        self.chatbot_browser.clear()
        self.plainTextEdit.clear()

    def handle_click_setting_btn(self):
        dlg = SettingDialog(self.iface, parent=self)
        dlg.setModal(True)
        dlg.show()
        dlg.exec()

    def on_chunks_info_received(self, content):
        """receive the count of references"""
        pass

    def on_content_received(self, content):
        """receive the streaming message."""
        # append every message to the chatbot browser.
        self.chatbot_browser.append_markdown(content)

    def on_stream_ended(self, chunk_count):
        self.chatbot_browser.post_process_markdown()
        self.btn_send_or_terminate_tag = 0
        self.btnSendOrTerminate.setText(self.tr("Send"))
        self.btnSendOrTerminate.setEnabled(True)

    def on_error_occurred(self, error_msg):
        """deal with errors"""
        # show errors in chatbot.
        self.chatbot_browser.append_markdown(error_msg)

        # resume button status.
        self.btn_send_or_terminate_tag = 0
        self.btnSendOrTerminate.setText(self.tr("Send"))
        self.btnSendOrTerminate.setEnabled(True)