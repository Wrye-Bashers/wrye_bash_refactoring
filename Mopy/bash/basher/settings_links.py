# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash; if not, write to the Free Software Foundation,
#  Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2019 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

import locale
import sys

from . import BashFrame, BashStatusBar
from .app_buttons import App_Button  # TODO(ut): ugly
from .dialogs import ColorDialog
from .. import barb, bush, balt, bass, bolt, env, exception
from ..balt import ItemLink, AppendableLink, RadioLink, CheckLink, MenuLink, \
    TransLink, EnabledLink, BoolLink, tooltip, Link
from ..bolt import deprint, GPath
from ..exception import BoltError
# TODO(ut): settings links do not seem to use Link.data attribute - it's None..

__all__ = ['Settings_BackupSettings', 'Settings_RestoreSettings',
           'Settings_SaveSettings', 'Settings_ExportDllInfo',
           'Settings_ImportDllInfo', 'Settings_Colors', 'Settings_IconSize',
           'Settings_UnHideButtons', 'Settings_StatusBar_ShowVersions',
           'Settings_Languages', 'Settings_PluginEncodings', 'Settings_Games',
           'Settings_UseAltName', 'Settings_Deprint',
           'Settings_DumpTranslator', 'Settings_UAC']

def _bassLang(): return bass.language if bass.language else \
    locale.getlocale()[0].split('_', 1)[0]
#------------------------------------------------------------------------------
# Settings Links --------------------------------------------------------------
#------------------------------------------------------------------------------
class Settings_BackupSettings(ItemLink):
    """Saves Bash's settings and user data.."""
    _text =_('Backup Settings...')
    _help = _("Backup all of Wrye Bash's settings/data to an archive file.")

    @balt.conversation
    def Execute(self):
        msg = _('Do you want to backup your Bash settings now?')
        if not balt.askYes(Link.Frame, msg,_('Backup Bash Settings?')): return
        with balt.BusyCursor(): BashFrame.SaveSettings(Link.Frame)
        base_dir = bass.settings['bash.backupPath'] or bass.dirs['modsBash']
        settings_file = balt.askSave(Link.Frame,
                                     title=_('Backup Bash Settings'),
                                     defaultDir=base_dir, wildcard='*.7z',
                                     defaultFile=barb.BackupSettings.
                                     backup_filename(bush.game.fsName))
        if not settings_file: return
        with balt.BusyCursor():
            backup = barb.BackupSettings(settings_file, bush.game.fsName)
        try:
            with balt.BusyCursor(): backup.backup_settings(balt)
        except exception.StateError:
            deprint('Backup settings failed', traceback=True)
            backup.warn_message(balt)

#------------------------------------------------------------------------------
class Settings_RestoreSettings(ItemLink):
    """Restore Bash's settings and user data from backup."""
    _text = _('Restore Settings...')
    _help = _("Restore all of Wrye Bash's settings/data from a backup archive "
             "file.")

    @balt.conversation
    def Execute(self):
        if not balt.askYes(Link.Frame, '\n\n'.join([
            _('Do you want to restore your Bash settings from a backup?'),
            _('This will force a restart of Wrye Bash once your settings are '
              'restored.')]), _('Restore Bash Settings?')):
            return
        # former may be None
        base_dir = bass.settings['bash.backupPath'] or bass.dirs['modsBash']
        settings_file = balt.askOpen(Link.Frame, _('Restore Bash Settings'),
                                     base_dir, '', '*.7z')
        if not settings_file: return
        with balt.BusyCursor():
            restore_ = barb.RestoreSettings(settings_file)
        backup_dir = None
        restarting = False
        try:
            with balt.BusyCursor():
                backup_dir = restore_.extract_backup()
            error_msg, error_title = restore_.incompatible_backup_error(
                bush.game.fsName)
            if error_msg:
                balt.showError(Link.Frame, error_msg, error_title)
                return
            error_msg, error_title = restore_.incompatible_backup_warn()
            if error_msg and not balt.askWarning(Link.Frame, error_msg,
                                                 error_title):
                return
            restarting = True
            balt.showInfo(balt.Link.Frame, '\n'.join([
                _('Your Bash settings have been successfully extracted.'),
                _('Backup Path: ') + settings_file.s, '', _('Before the '
                  'settings can take effect, Wrye Bash must restart.'), _(
                'Click OK to restart now.')]), _('Bash Settings Extracted'))
            try: # we currently disallow backup and restore on the same boot
                bass.sys_argv.remove('--backup')
            except ValueError:
                pass
            Link.Frame.Restart(['--restore'], ['--filename', backup_dir.s])
        except BoltError as e:
            deprint('Restore settings failed:', traceback=True)
            restore_.warn_message(balt, e.message)
        finally:
            if not restarting and backup_dir is not None:
                barb.RestoreSettings.remove_extract_dir(backup_dir)

#------------------------------------------------------------------------------
class Settings_SaveSettings(ItemLink):
    """Saves Bash's settings and user data."""
    _text = _('Save Settings')
    _help = _("Save all of Wrye Bash's settings/data now.")

    def Execute(self):
        BashFrame.SaveSettings(Link.Frame)

#------------------------------------------------------------------------------
class Settings_ExportDllInfo(AppendableLink, ItemLink):
    """Exports list of good and bad dll's."""
    _text = _("Export list of allowed/disallowed %s plugin DLLs") % \
        bush.game.se.se_abbrev
    _help = _("Export list of allowed/disallowed plugin DLLs to a txt file"
              " (for BAIN).")

    def _append(self, window): return bool(bush.game.se.se_abbrev or
                                           bush.game.sd.sd_abbrev)

    def Execute(self):
        textDir = bass.dirs['patches']
        textDir.makedirs()
        #--File dialog
        title = _('Export list of allowed/disallowed plugin DLLs to:')
        file_ = bush.game.se.se_abbrev + ' ' + _('DLL permissions') + '.txt'
        textPath = self._askSave(title=title, defaultDir=textDir,
                                 defaultFile=file_, wildcard='*.txt')
        if not textPath: return
        with textPath.open('w',encoding='utf-8-sig') as out:
            out.write('goodDlls '+_('(those dlls that you have chosen to allow to be installed)')+'\r\n')
            if bass.settings['bash.installers.goodDlls']:
                for dll in bass.settings['bash.installers.goodDlls']:
                    out.write('dll:'+dll+':\r\n')
                    for index, version in enumerate(bass.settings['bash.installers.goodDlls'][dll]):
                        out.write('version %02d: %s\r\n' % (index, version))
            else: out.write('None\r\n')
            out.write('badDlls '+_('(those dlls that you have chosen to NOT allow to be installed)')+'\r\n')
            if bass.settings['bash.installers.badDlls']:
                for dll in bass.settings['bash.installers.badDlls']:
                    out.write('dll:'+dll+':\r\n')
                    for index, version in enumerate(bass.settings['bash.installers.badDlls'][dll]):
                        out.write('version %02d: %s\r\n' % (index, version))
            else: out.write('None\r\n')

#------------------------------------------------------------------------------
class Settings_ImportDllInfo(AppendableLink, ItemLink):
    """Imports list of good and bad dll's."""
    _text = _("Import list of allowed/disallowed %s plugin DLLs") % \
        bush.game.se.se_abbrev
    _help = _("Import list of allowed/disallowed plugin DLLs from a txt file"
        " (for BAIN).")

    def _append(self, window): return bool(bush.game.se.se_abbrev or
                                           bush.game.sd.sd_abbrev)

    def Execute(self):
        textDir = bass.dirs['patches']
        textDir.makedirs()
        #--File dialog
        defFile = bush.game.se.se_abbrev + ' ' + _(
            'dll permissions') + '.txt'
        title = _('Import list of allowed/disallowed plugin DLLs from:')
        textPath = self._askOpen(title=title, defaultDir=textDir,
                                 defaultFile=defFile, wildcard='*.txt',
                                 mustExist=True)
        if not textPath: return
        message = (_('Merge permissions from file with current dll permissions?')
                   + '\n' +
                   _("('No' Replaces current permissions instead.)")
                   )
        replace = not balt.askYes(Link.Frame, message,
                                  _('Merge permissions?'))
        try:
            with textPath.open('r',encoding='utf-8-sig') as ins:
                Dlls = {'goodDlls':{},'badDlls':{}}
                for line in ins:
                    line = line.strip()
                    if line.startswith('goodDlls'):
                        current = Dlls['goodDlls']
                    if line.startswith('badDlls'):
                        current = Dlls['badDlls']
                    elif line.startswith('dll:'):
                        dll = line.split(':',1)[1].strip()
                        current.setdefault(dll,[])
                    elif line.startswith('version'):
                        ver = line.split(':',1)[1]
                        ver = eval(ver)
                        current[dll].append(ver)
                        print(dll,':',ver)
            if not replace:
                bass.settings['bash.installers.goodDlls'].update(Dlls['goodDlls'])
                bass.settings['bash.installers.badDlls'].update(Dlls['badDlls'])
            else:
                bass.settings['bash.installers.goodDlls'], bass.settings['bash.installers.badDlls'] = Dlls['goodDlls'], Dlls['badDlls']
        except UnicodeError:
            self._showError(_('Wrye Bash could not load %s, because it is not'
                              ' saved in UTF-8 format.  Please resave it in '
                              'UTF-8 format and try again.') % textPath.s)
        except Exception as e:
            deprint('Error reading', textPath.s, traceback=True)
            self._showError(_('Wrye Bash could not load %s, because there was'
                              ' an error in the format of the file.')
                            % textPath.s)

#------------------------------------------------------------------------------
class Settings_Colors(ItemLink):
    """Shows the color configuration dialog."""
    _text = _('Colors...')
    _help = _("Configure the custom colors used in the UI.")

    def Execute(self): ColorDialog.Display()

#------------------------------------------------------------------------------
class Settings_IconSize(RadioLink):
    def __init__(self, sb_icon_size):
        super(Settings_IconSize, self).__init__()
        self.sb_icon_size = sb_icon_size
        self._text = str(sb_icon_size)
        self._help = _("Sets the status bar icons to %(sb_icon_size)s pixels") % (
            {'sb_icon_size': str(sb_icon_size)})

    def _check(self):
        return self.sb_icon_size == bass.settings['bash.statusbar.iconSize']

    def Execute(self):
        bass.settings['bash.statusbar.iconSize'] = self.sb_icon_size
        Link.Frame.statusBar.UpdateIconSizes()

#------------------------------------------------------------------------------
class Settings_StatusBar_ShowVersions(CheckLink):
    """Show/Hide version numbers for buttons on the statusbar."""
    _text = _('Show App Version')
    _help = _("Show/hide version numbers for buttons on the status bar.")

    def _check(self): return bass.settings['bash.statusbar.showversion']

    def Execute(self):
        bass.settings['bash.statusbar.showversion'] ^= True
        for button in BashStatusBar.buttons:
            if isinstance(button, App_Button):
                if button.gButton:
                    button.gButton.SetToolTip(tooltip(button.sb_button_tip))
        if BashStatusBar.obseButton.button_state:
            for button in App_Button.obseButtons:
                button.gButton.SetToolTip(tooltip(getattr(button,'obseTip','')))

#------------------------------------------------------------------------------
class Settings_Languages(TransLink):
    """Menu for available Languages."""
    def _decide(self, window, selection):
        languages = []
        for f in bass.dirs['l10n'].list():
            if f.cext == '.txt' and f.csbody[-3:] != 'new':
                languages.append(f.body)
        if languages:
            subMenu = MenuLink(_('Language'))
            for lang in languages:
                subMenu.links.append(_Settings_Language(lang.s))
            if GPath('english') not in languages:
                subMenu.links.append(_Settings_Language('English'))
            return subMenu
        else:
            class _NoLang(EnabledLink):
                _text = _('Language')
                _help = _("Wrye Bash was unable to detect any translation"
                         " files.")
                def _enable(self): return False
            return _NoLang()

#------------------------------------------------------------------------------
class _Settings_Language(EnabledLink, RadioLink):
    """Specific language for Wrye Bash."""
    languageMap = {
        'chinese (simplified)': _('Chinese (Simplified)') + ' (简体中文)',
        'chinese (traditional)': _('Chinese (Traditional)') + ' (繁体中文)',
        'de': _('German') + ' (Deutsch)',
        'pt_opt': _('Portuguese') + ' (português)',
        'italian': _('Italian') + ' (italiano)',
        'russian': _('Russian') + ' (ру́сский язы́к)',
        'english': _('English') + ' (English)',
        }

    def __init__(self, lang):
        super(_Settings_Language, self).__init__()
        self._lang = lang
        self._text = self.__class__.languageMap.get(self._lang.lower(),
                                                    self._lang)

    def _initData(self, window, selection):
        if self._lang == _bassLang():
            self._help = _("Currently using %(languagename)s as the active "
                          "language.") % ({'languagename': self._text})
            self.check = True
        else:
            self._help = _(
                "Restart Wrye Bash and use %(languagename)s as the active "
                "language.") % ({'languagename': self._text})
            self.check = False

    def _check(self): return self.check

    def _enable(self): return not self.check

    def Execute(self):
        if balt.askYes(Link.Frame,
                _('Wrye Bash needs to restart to change languages.  Do you '
                  'want to restart?'), _('Restart Wrye Bash')):
            Link.Frame.Restart(['--Language', self._lang])

#------------------------------------------------------------------------------
class Settings_PluginEncodings(MenuLink):
    _plugin_encodings = {
        'gbk': _('Chinese (Simplified)'),
        'big5': _('Chinese (Traditional)'),
        'cp1251': _('Russian'),
        'cp932': _('Japanese (Shift_JIS)'),
        'utf-8': _('UTF-8'),
        'cp1252': _('Western European (English, French, German, etc)'),
        }
    def __init__(self):
        super(Settings_PluginEncodings, self).__init__(_('Plugin Encoding'))
        self.links.append(Settings_PluginEncoding(_('Automatic'),None))
        # self.links.append(SeparatorLink())
        enc_name = sorted(list(self._plugin_encodings.items()), key=lambda x: x[1])
        for encoding,name in enc_name:
            self.links.append(Settings_PluginEncoding(name,encoding))

#------------------------------------------------------------------------------
class Settings_PluginEncoding(RadioLink):
    def __init__(self,name,encoding):
        super(Settings_PluginEncoding, self).__init__()
        self._text = name
        self.encoding = encoding
        self._help = _("Select %(encodingname)s encoding for Wrye Bash to use."
            ) % ({'encodingname': self._text})

    def _check(self): return self.encoding == bass.settings[
        'bash.pluginEncoding']

    def Execute(self):
        bass.settings['bash.pluginEncoding'] = self.encoding
        bolt.pluginEncoding = self.encoding

#------------------------------------------------------------------------------
class Settings_Games(MenuLink):

    def __init__(self):
        super(Settings_Games, self).__init__(_('Game'))
        for fsName in bush.foundGames:
            self.links.append(_Settings_Game(fsName))

class _Settings_Game(RadioLink):
    def __init__(self,game):
        super(_Settings_Game, self).__init__()
        self._text = bush.get_display_name(game)
        self._help = _("Restart Wrye Bash to manage %(game)s.") % (
            {'game': self._text})

    def _check(self): return self._text == bush.game.displayName

    def Execute(self):
        if self._check(): return
        if not balt.askContinue(Link.Frame,
                                _('Note: Switching games this way will '
                                  'simply relaunch this Wrye Bash '
                                  'installation with the -o command line '
                                  'switch.\n\nThat means manually added '
                                  'application launchers in the status bar '
                                  'will not change after switching.'),
                                'bash.switch_games_warning.shown'):
            return
        Link.Frame.Restart(['--oblivionPath', bush.game_path(self._text).s])

#------------------------------------------------------------------------------
class Settings_UnHideButtons(TransLink):
    """Menu to unhide a StatusBar button."""

    def _decide(self, window, selection):
        hide = bass.settings['bash.statusbar.hide']
        hidden = []
        for link in BashStatusBar.buttons:
            if link.uid in hide:
                hidden.append(link)
        if hidden:
            subMenu = MenuLink(_('Unhide Buttons'))
            for link in hidden:
                subMenu.links.append(Settings_UnHideButton(link))
            return subMenu
        else:
            class _NoButtons(EnabledLink):
                _text = _('Unhide Buttons')
                _help = _("No hidden buttons available to unhide.")
                def _enable(self): return False
            return _NoButtons()

#------------------------------------------------------------------------------
class Settings_UnHideButton(ItemLink):
    """Unhide a specific StatusBar button."""
    def __init__(self,link):
        super(Settings_UnHideButton, self).__init__()
        self.link = link
        button = self.link.gButton
        # Get a title for the hidden button
        if button:
            # If the wx.Button object exists (it was hidden this session),
            # Use the tooltip from it
            tip_ = button.GetToolTip().GetTip()
        else:
            # If the link is an App_Button, it will have a 'sb_button_tip' attribute
            tip_ = getattr(self.link,'sb_button_tip',None) # YAK YAK YAK
        if tip_ is None:
            # No good, use its uid as a last resort
            tip_ = self.link.uid
        self._text = tip_
        self._help = _("Unhide the '%s' status bar button.") % tip_

    def Execute(self): Link.Frame.statusBar.UnhideButton(self.link)

#------------------------------------------------------------------------------
class Settings_UseAltName(BoolLink):
    _text, key, _help = _('Use Alternate Wrye Bash Name'), 'bash.useAltName',\
        _('Use an alternate display name for Wrye Bash based on the game it'
          ' is managing.')

    def Execute(self):
        super(Settings_UseAltName, self).Execute()
        Link.Frame.SetTitle()

#------------------------------------------------------------------------------
class Settings_UAC(AppendableLink, ItemLink):
    _text = _('Administrator Mode')
    _help = _('Restart Wrye Bash with administrator privileges.')

    def _append(self, window): return env.isUAC

    def Execute(self):
        if balt.askYes(Link.Frame,
                _('Restart Wrye Bash with administrator privileges?'),
                _('Administrator Mode'), ):
            Link.Frame.Restart(['--uac'])

class Settings_Deprint(CheckLink):
    """Turn on deprint/delist."""
    _text = _('Debug Mode')
    _help = _("Turns on extra debug prints to help debug an error or just for "
             "advanced testing.")

    def _check(self): return bolt.deprintOn

    def Execute(self):
        deprint(_('Debug Printing: Off'))
        bolt.deprintOn = not bolt.deprintOn
        deprint(_('Debug Printing: On'))

class Settings_DumpTranslator(AppendableLink, ItemLink):
    """Dumps new translation key file using existing key, value pairs."""
    _text = _('Dump Translator')
    _help = _("Generate a new version of the translator file for your locale.")

    def _append(self, window):
        """Can't dump the strings if the files don't exist."""
        return not hasattr(sys,'frozen')

    def Execute(self):
        message = _('Generate Bash program translator file?') + '\n\n' + _(
            'This function is for translating Bash itself (NOT mods) into '
            'non-English languages.  For more info, '
            'see Internationalization section of Bash readme.')
        if not self._askContinue(message, 'bash.dumpTranslator.continue',
                                _('Dump Translator')): return
        outPath = bass.dirs['l10n']
        with balt.BusyCursor():
            outFile = bolt.dumpTranslator(outPath.s, _bassLang())
        self._showOk(_(
            'Translation keys written to ') + 'Mopy\\bash\\l10n\\' + outFile,
                     _('Dump Translator') + ': ' + outPath.stail)
