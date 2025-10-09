# -*- coding: utf-8 -*-
"""
/***************************************************************************
                        Chinese AI Assistant Plugin
 This plugin provides a QGIS assistant, combining a LLM with the Phoenix-GIS
 knowledge database.
                             -------------------
        begin                : 2025-09-29
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
 This script initializes the plugin, making it known to QGIS.
"""

# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load ChineseAIAssistant class from file ChineseAIAssistant.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .chinese_ai_assistant import ChineseAIAssistant
    return ChineseAIAssistant(iface)
