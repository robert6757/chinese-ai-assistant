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

from PyQt5.QtCore import QByteArray, Qt, QUrl
from PyQt5.QtGui import QTextDocument, QImage
from PyQt5.QtWidgets import QTextBrowser

class ChatbotBrowser(QTextBrowser):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.markdown_content = ""

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

            # Fetch the image from the internet
            try:
                response = requests.get(url_string, timeout=(2, 2))
                if response.status_code == 200:
                    image_data = QByteArray(response.content)
                    image = QImage()
                    if image.loadFromData(image_data):
                        # Add the image to the cache and return it
                        # In order to fit the window, we scaled the image.
                        scaled_width = self.size().width()
                        scaled_image = image.scaled(
                            scaled_width,
                            image.height() * scaled_width // image.width(),
                            Qt.KeepAspectRatio,
                            Qt.SmoothTransformation
                        )
                        self.image_cache[url_string] = scaled_image
                        return scaled_image
            except requests.exceptions.Timeout:
                self.iface.messageBar().pushMessage(self.tr("Request timeout.") + url_string)
                self.image_cache[url_string] = None
                return None
            except requests.exceptions.ConnectionError as e:
                self.iface.messageBar().pushMessage(self.tr("Connection error.") + url_string)
                self.image_cache[url_string] = None
                return None
            except requests.exceptions.RequestException as e:
                self.iface.messageBar().pushMessage(self.tr("Request failed.") + url_string)
                self.image_cache[url_string] = None
                return None
            except Exception as e:
                self.iface.messageBar().pushMessage(self.tr("Unexpected error loading image.") + url_string)
                self.image_cache[url_string] = None
                return None
        # Do not load unknown format of resource.
        return None

    def append_markdown(self, content: str):
        self.markdown_content += content

        # update markdown content
        self.setMarkdown(self.markdown_content)

        # scroll to bottom.
        self.scroll_to_bottom()

    def post_process_markdown(self):
        self.markdown_content += "\n\n---------\n\n"

        # deal with upl-image-preview block.
        self.markdown_content = self.convert_upl_to_markdown_image(self.markdown_content)

        # replace failed image with links.
        self.markdown_content = self.replace_failed_images_with_links(self.markdown_content)

        self.setMarkdown(self.markdown_content)
        self.scroll_to_bottom()

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

    def scroll_to_bottom(self):
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def handle_click_chatbot_anchor(self, link: QUrl):
        url_str = link.url()
        webbrowser.open(url_str)

    def convert_upl_to_markdown_image(self, markdown_text):
        # regex: [upl-image-preview ...]
        pattern = r'\[upl-image-preview[^\]]*?url=([^\s\]]+)[^\]]*\]'
        converted_text = re.sub(pattern, r'\n\n![Image](\1)', markdown_text)
        return converted_text

