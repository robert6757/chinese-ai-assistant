"""
/***************************************************************************
                               Chatbot Browser
 A class inherits from QTextBrowser to display chatbot content.

        begin                : 2025-10-09
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

import requests
import webbrowser
import re

from PyQt5.QtCore import QByteArray, Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QTextDocument, QImage, QMouseEvent
from PyQt5.QtWidgets import QTextBrowser

class ChatbotBrowser(QTextBrowser):

    show_setting_dlg = pyqtSignal()

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.markdown_content = ""
        self.auto_scroll_to_bottom = True

        # Use a dictionary to cache downloaded images to prevent multiple downloads
        self.image_cache = {}

        self.anchorClicked.connect(self.handle_click_chatbot_anchor)

    def loadResource(self, type, name):
        """
        Overrides the standard loadResource method to handle network requests for images.
        """
        if type == QTextDocument.ImageResource and name.scheme() in ('http', 'https'):
            url_string = name.toString()
            # Check if the image is already in the cache
            if url_string in self.image_cache:
                return self.image_cache[url_string]

            try:
                response = requests.get(url_string, timeout=(1, 2))
                # raise exception for http code.
                response.raise_for_status()

                image_data = QByteArray(response.content)
                image = QImage()
                if not image.loadFromData(image_data):
                    raise ValueError("Failed to load image from data")

                # Add the image to the cache and return it
                scaled_width = self.size().width()
                scaled_image = image.scaled(
                    scaled_width,
                    image.height() * scaled_width // image.width(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.image_cache[url_string] = scaled_image
                return scaled_image

            except Exception as e:
                # catch all exceptions.
                error_msg = f"Error loading image: {url_string}: {str(e)}"
                self.iface.messageBar().pushMessage(error_msg)
                self.image_cache[url_string] = None
                return None

        # Do not load unknown format of resource.
        return None

    def append_markdown(self, content: str):
        # save current scroll value.
        scrollbar = self.verticalScrollBar()
        current_scroll_value = scrollbar.value()

        self.markdown_content += content

        # update markdown content
        self.setMarkdown(self.markdown_content)

        if self.auto_scroll_to_bottom:
            self.scroll_to_bottom()
        else:
            # resume scroll bar value.
            scrollbar.setValue(current_scroll_value)

    def pre_process_markdown(self):
        # resume auto scroll to bottom.
        self.auto_scroll_to_bottom = True

    def post_process_markdown(self):
        # save current scroll value.
        scrollbar = self.verticalScrollBar()
        current_scroll_value = scrollbar.value()

        self.markdown_content += "\n\n---------\n\n"

        # deal with upl-image-preview block.
        self.markdown_content = self.convert_upl_to_markdown_image(self.markdown_content)

        # replace failed image with links.
        self.markdown_content = self.replace_failed_images_with_links(self.markdown_content)

        self.setMarkdown(self.markdown_content)

        if self.auto_scroll_to_bottom:
            self.scroll_to_bottom()
        else:
            # resume the score value.
            scrollbar.setValue(current_scroll_value)

        # Check Result!
        # self.iface.messageBar().pushMessage(self.markdown_content)

    def replace_failed_images_with_links(self, markdown_text):
        # Markdown format: ![alt](url)
        pattern = r'!\[([^\]]*)\]\(([^)]+)\)'

        def replace_match(match):
            alt_text = match.group(1)
            url = match.group(2)

            if url in self.image_cache and self.image_cache[url] is None:
                # replace to href.
                return f'[{alt_text}]({url})'
            else:
                # keep strings.
                return match.group(0)

        return re.sub(pattern, replace_match, markdown_text)

    def clear(self):
        self.markdown_content = ""
        self.setMarkdown("")
        self.image_cache.clear()
        self.auto_scroll_to_bottom = True

    def scroll_to_bottom(self):
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def mousePressEvent(self, event: QMouseEvent):
        # forbid auto scroll to bottom
        self.auto_scroll_to_bottom = False
        super().mousePressEvent(event)

    def wheelEvent(self, event):
        # forbid auto scroll to bottom
        self.auto_scroll_to_bottom = False
        super().wheelEvent(event)

    def handle_click_chatbot_anchor(self, link: QUrl):
        if link.scheme() == "agent":
            # use agent to process.
            process_name = link.host()
            if process_name == "applyvip":
                self.show_setting_dlg.emit()
            return

        # open web browser
        url_str = link.url()
        webbrowser.open(url_str)

    def convert_upl_to_markdown_image(self, markdown_text):
        # regex: [upl-image-preview ...]
        pattern = r'\[upl-image-preview[^\]]*?url=([^\s\]]+)[^\]]*\]'
        converted_text = re.sub(pattern, r'\n\n![Image](\1)', markdown_text, flags=re.IGNORECASE)
        return converted_text

