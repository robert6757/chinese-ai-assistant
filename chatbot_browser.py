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
import time
from threading import Lock

from PyQt5.QtCore import QByteArray, Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QTextDocument, QImage, QMouseEvent
from PyQt5.QtWidgets import QTextBrowser

class ChatbotBrowser(QTextBrowser):

    show_setting_dlg = pyqtSignal()
    trigger_feedback = pyqtSignal(int)

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.markdown_content = ""
        self.auto_scroll_to_bottom = True

        # Use a dictionary to cache downloaded images to prevent multiple downloads
        self.image_cache = {}

        self.method_lock = Lock()

        self.anchorClicked.connect(self.handle_click_chatbot_anchor)

        self.setMouseTracking(True)

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
                # using stream mode, manually control loading image.
                downloading_start_time = time.time()

                # in order to shorten loading time, timeout is only 1.
                response = requests.get(url_string, timeout=1, stream=True)
                response.raise_for_status()

                # control downloading time.
                content_chunks = []
                for chunk in response.iter_content(chunk_size=8192):
                    if time.time() - downloading_start_time > 3:
                        raise requests.exceptions.Timeout("Download image took too long")

                    if chunk:
                        content_chunks.append(chunk)

                # combine all chunks.
                image_data = QByteArray(b''.join(content_chunks))
                image = QImage()
                if not image.loadFromData(image_data):
                    raise ValueError("Failed to load image from data")

                # Add the image to the cache and return it
                available_width = self.size().width()
                if image.width() > available_width:
                    scaled_image = image.scaledToWidth(available_width, Qt.SmoothTransformation)
                else:
                    scaled_image = image

                self.image_cache[url_string] = scaled_image
                return scaled_image

            except requests.exceptions.Timeout:
                # timeout exception.
                error_msg = f"Image download timeout: {url_string}"
                self.iface.messageBar().pushMessage(error_msg)
                self.image_cache[url_string] = None
                return None
            except Exception as e:
                # catch all exceptions.
                error_msg = f"Error loading image: {url_string}: {str(e)}"
                self.iface.messageBar().pushMessage(error_msg)
                self.image_cache[url_string] = None
                return None

        # Do not load unknown format of resource.
        return None

    def append_markdown(self, content: str, scroll_to_bottom=True):
        # acquire lock
        if not self.method_lock.acquire(blocking=False):
            # only append to variable without really drawing it.
            self.markdown_content += content
            return

        try:
            # save current scroll value.
            scrollbar = self.verticalScrollBar()
            current_scroll_value = scrollbar.value()

            self.markdown_content += content

            # update markdown content
            self.setMarkdown(self.markdown_content)

            if scroll_to_bottom and self.auto_scroll_to_bottom:
                self.scroll_to_bottom()
            else:
                # resume scroll bar value.
                scrollbar.setValue(current_scroll_value)
        finally:
            # release lock
            self.method_lock.release()

    def pre_process_markdown(self):
        # resume auto scroll to bottom.
        self.auto_scroll_to_bottom = True

    def post_process_markdown(self, show_feedback = True):
        # save current scroll value.
        scrollbar = self.verticalScrollBar()
        current_scroll_value = scrollbar.value()

        # add feedback
        if show_feedback:
            self.markdown_content += "\n\n" + self.tr("Was this answer helpful? [Yes](agent://feedback/5) | [No](agent://feedback/1)")

        self.markdown_content += "\n\n---------\n\n"

        # deal with upl-image-preview block.
        self.markdown_content = self.convert_upl_to_markdown_image(self.markdown_content)

        # replace failed image with links.
        self.markdown_content = self.replace_failed_images_with_links(self.markdown_content)

        # clean all html tags
        self.markdown_content = self.clean_html_tag(self.markdown_content)

        self.setMarkdown(self.markdown_content)

        if self.auto_scroll_to_bottom:
            self.scroll_to_bottom()
        else:
            # resume the scroll value.
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

    def clean_html_tag(self, markdown_text):
        return re.sub(r'<\/?[a-zA-Z][^>]*>', '', markdown_text)

    def clear(self):
        self.markdown_content = ""
        self.setMarkdown("")
        self.image_cache.clear()
        self.auto_scroll_to_bottom = True

    def scroll_to_bottom(self):
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

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
            elif process_name == "feedback":
                self.trigger_feedback.emit(int(link.path()[1:]))
            return

        # open web browser
        url_str = link.url()
        webbrowser.open(url_str)

    def convert_upl_to_markdown_image(self, markdown_text):
        # regex: [upl-image-preview ...]
        pattern = r'\[upl-image-preview[^\]]*?url=([^\s\]]+)[^\]]*\]'
        converted_text = re.sub(pattern, r'\n\n![Image](\1)', markdown_text, flags=re.IGNORECASE)
        return converted_text

    def get_raw_markdown_content(self):
        self.method_lock.acquire()
        try:
            return self.markdown_content
        finally:
            self.method_lock.release()

    def mousePressEvent(self, event: QMouseEvent):
        # forbid auto scroll to bottom
        self.auto_scroll_to_bottom = False

        try:
            # Check if clicked on an image
            cursor = self.cursorForPosition(event.pos())
            if cursor:
                char_format = cursor.charFormat()
                if char_format.isValid():
                    image_format = char_format.toImageFormat()
                    if image_format.isValid():
                        image_name = image_format.name()
                        if image_name:
                            # If clicked on an image, handle it
                            self._handle_image_click(image_name)
                            return
        except Exception as e:
            # show error message.
            error_msg = f"Error in mousePressEvent: {e}"
            self.iface.messageBar().pushMessage(error_msg)

        # Otherwise, call parent's mousePressEvent
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        # check hyperlink first.
        anchor = self.anchorAt(event.pos())

        if anchor:
            # use hand cursor on hyperlink text.
            self.viewport().setCursor(Qt.PointingHandCursor)
        else:
            # whether moving on image.
            try:
                cursor = self.cursorForPosition(event.pos())
                if cursor:
                    char_format = cursor.charFormat()
                    if char_format.isValid():
                        image_format = char_format.toImageFormat()
                        if image_format.isValid():
                            image_name = image_format.name()
                            if image_name:
                                # use hand cursor on image.
                                self.viewport().setCursor(Qt.PointingHandCursor)
                                super().mouseMoveEvent(event)
                                return
            except Exception as e:
                error_msg = f"Error in mouseMoveEvent: {e}"
                self.iface.messageBar().pushMessage(error_msg)

            # use default cursor.
            self.viewport().setCursor(Qt.ArrowCursor)

        super().mouseMoveEvent(event)

    def _handle_image_click(self, image_url):
        """
        Handle click on an image. Try to extract the original URL from the image.
        """
        try:
            # The image_url might be a QUrl or a string
            if isinstance(image_url, QUrl):
                url_str = image_url.toString()
            else:
                url_str = str(image_url)

            # Check if it's a network URL
            if url_str.startswith(('http://', 'https://')):
                # Open the image in browser
                webbrowser.open(url_str)
            else:
                # Try to find the original URL in the markdown content
                # Look for markdown image syntax with this URL
                pattern = r'!\[[^\]]*\]\(([^)]+)\)'
                matches = re.findall(pattern, self.markdown_content)

                for match in matches:
                    if url_str in match or match in url_str:
                        webbrowser.open(match)
                        return
        except Exception as e:
            # show error message.
            error_msg = f"Error in _handle_image_click: {e}"
            self.iface.messageBar().pushMessage(error_msg)