#!/usr/bin/env python3


import os
import stat
import yaml
import base64
import tempfile
import subprocess
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class SecureConfig:
    '''
    A class for securely handling configuration files for a specific tool.
    
    The class manages configuration paths and provides encryption and decryption for sensitive configuration YAMLs.

    :param tool_name: The name of the tool.
    :type tool_name: str
    :param config_path: An optional path to the configuration file. If not provided, the default config path will be used.
    :type config_path: Path, optional
    '''
    def __init__(self, tool_name: str, config_path: Path = None):
        '''
        Initializes the SecureConfig object with a tool name and configuration path.
        If no configuration path is provided, the default configuration path will be used.

        :param tool_name: The name of the tool.
        :type tool_name: str
        :param config_path: An optional path to the configuration file. If not provided, the default config path will be used.
        :type config_path: Path, optional
        '''
        self.tool_name = tool_name
        self.b_tool_name = tool_name.encode('utf-8')
        self.mngt = b"# MANAGED BY " + self.b_tool_name + b" #\n"
        if config_path is not None:
            self.config_path = config_path if isinstance(config_path, Path) else Path(config_path)
        else:
            self.config_path = self._get_default_config_path()
        self._fernet: Optional[Fernet] = None



    def _get_default_config_path(self) -> Path:
        '''
        Default configuration path.
        :return: Path to the configuration file
        :rtype: Path
        '''
        if os.name == 'nt':  # Windows
            base_path = Path(os.environ.get('APPDATA', Path.home()))
            config_dir = base_path / self.tool_name
        elif os.name == 'posix':  # Linux/Unix/macOS
            base_path = Path.home()
            if os.path.exists('/Library'):  # macOS
                config_dir = base_path / 'Library' / 'Application Support' / self.tool_name
            else:  # Linux/Unix
                config_dir = base_path / '.config' / self.tool_name
        
        # Create directory with secure permissions
        config_dir.mkdir(parents=True, exist_ok=True)
        if os.name == 'posix':
            os.chmod(config_dir, stat.S_IRWXU)
        settings_path_yaml = Path.joinpath(config_dir, 'settings.yaml')
        settings_path_yml = Path.joinpath(config_dir, 'settings.yml')
        if settings_path_yaml.is_file():
            return settings_path_yaml
        elif settings_path_yml.is_file():
            return settings_path_yml
        raise SystemExit(f"settings.yaml does not exists, please check {config_dir}\
                         \nOr make a new one with 'saber -x' and 'saber -e PATH'")



    def get_config_path(self) -> Path:
        '''
        Return stored configuration path.
        :return: Path to the configuration file
        :rtype: Path
        '''
        return self.config_path

    

    def _derive_key(self, password: str) -> bytes:
        '''
        Key Derivation from passoword using PBKDF2HMAC and SHA256.
        Currently the salt is static.

        :type password: str
        :param password: String for key derivation.
        '''
        static_salt = b'static_salt_value_777' # TODO: Use seasoning properly
            
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=static_salt,
            iterations=100000
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key



    def _set_secure_permissions(self):
        '''
        Set secure permitions on configuration file, mode 600 un unix systems.
        '''
        if os.name == 'posix':
            os.chmod(self.config_path, stat.S_IRUSR | stat.S_IWUSR)  # 600 permissions



    def encrypt_data(self, data: bytes) -> bytes:
        '''
        Data encryption with Fernet.

        :type data: bytes
        :param data: Data to encrypt
        '''
        if not self._fernet:
            raise ValueError("Encryption not initialized. Call initialize_encryption first.")
        return self._add_newlines(self._fernet.encrypt(data))



    def decrypt_data(self, encrypted_data: bytes) -> bytes:
        '''
        Data decryption with Fernet.

        :type data: bytes
        :param data: Data to decrypt
        '''
        if not self._fernet:
            raise ValueError("Encryption not initialized. Call initialize_encryption first.")
        return self._fernet.decrypt(self._remove_newlines(encrypted_data))



    def initialize_encryption(self, password: str):
        '''
        Fernet initialization with derived key.

        :type password: str
        :param password: String for key derivation.
        '''
        key = self._derive_key(password)
        self._fernet = Fernet(key)



    def is_encrypted(self) -> bool:
        '''
        Checks whether the configuration file is encrypted.

        The function check for the presence of a string at the beginning of the file.
        If present the function assumes that the file is encrypted by the same python tool.

        :return: True if the configuration file is encrypted, otherwise False.
        :rtype: bool
        '''
        try:
            with open(self.config_path, 'rb') as f:
                data = f.readline()
                
            if data == self.mngt:
                return True
            else:
                return False
            
        except Exception:
            return False



    def _write_file(self, data: bytes):
        '''
        Write a file using a tempfile and atomically replace it in the configuration path.
        If it fails it will use the same directory to create a temporary file and use rename, 
        for the atomic substitution.
        
        :type data: bytes
        :param data: Data to write on file
        '''
        # Try using tempfile and replace, can fail in some cases
        try:
            with tempfile.NamedTemporaryFile(mode='wb', delete=False) as tmp_file:
                tmp_file.write(data)
                tmp_file.flush()  # Ensure data is written
                os.fsync(tmp_file.fileno())  # Force write to disk
                tmp_path = Path(tmp_file.name)
            
            os.chmod(tmp_path, stat.S_IRUSR | stat.S_IWUSR)
            
            os.replace(tmp_path, self.config_path) # Either succed or fails to replace file 

        except OSError:
            # Fallback: Use same-directory temporary file
            temp_path = self.config_path.with_suffix('.tmp')
            try:
                # Write encrypted data to temporary file
                with open(temp_path, 'wb') as f:
                    f.write(data)
                    f.flush()
                    os.fsync(f.fileno())
                
                os.chmod(temp_path, stat.S_IRUSR | stat.S_IWUSR)
                
                os.rename(temp_path, self.config_path)  # Still atomic like replace
                
            except Exception as e:
                # Clean up
                if temp_path.exists():
                    try:
                        os.unlink(temp_path)
                    except Exception:
                        pass
                raise e



    def encrypt_existing_file(self):
        '''
        Encrypt an existing configuration YAML file. Validates YAML format before encryption
        '''
        if not self._fernet:
            raise ValueError("Encryption not initialized. Call initialize_encryption first.")
            
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file {self.config_path} not found")
            
        if not self.is_encrypted():
            
            # Read and validate the existing YAML file
            with open(self.config_path, 'rb') as f:
                yaml_data = f.read()
    
            if yaml_data and not yaml_data.endswith(b"\n"):
                yaml_data += b"\n"
            
            # Validate YAML format before encryption
            try:
                yaml.safe_load(yaml_data)
            except yaml.YAMLError:
                raise ValueError("Invalid YAML data in configuration file")
                    
            # Encrypt the existing content
            encrypted_data = self.mngt + self.encrypt_data(yaml_data) + b"\n"

            self._write_file(encrypted_data)

        else:
            return



    def decrypt_existing_file(self):
        '''
        Decrypt an existing configuration YAML file.
        '''
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file {self.config_path} not found")
            
        if self.is_encrypted():
            if not self._fernet:
                raise ValueError("Encryption not initialized. Call initialize_encryption first.")
            
            with open(self.config_path, 'rb') as f:
                f.readline()
                encrypted_data = f.read()
                if encrypted_data.endswith(b"\n"):
                    encrypted_data = encrypted_data[:-1]
                        
            decrypted_data = self.decrypt_data(encrypted_data)
            if decrypted_data and not decrypted_data.endswith(b"\n"):
                decrypted_data += b"\n"

            self._write_file(decrypted_data)
            
        else:
            
            return

        
    
    def save_config(self, config_data: dict):
        '''
        Save encrypted data to configuration file.

        :type config_data: dict
        :param config_data: Dictionary containing configuration data
        '''
        if not self._fernet:
            raise ValueError("Encryption not initialized. Call initialize_encryption first.")
            
        yaml_data = yaml.dump(config_data).encode()

        if yaml_data and not yaml_data.endswith(b"\n"):
            yaml_data += b"\n"

        encrypted_data = self.mngt + self.encrypt_data(yaml_data) + b"\n"
        
        self._write_file(encrypted_data)

        self._set_secure_permissions()



    def load_config(self) -> dict:
        '''
        Load configuration from YAML file whether is encrypted or not.

        :return: Configuration dictionary
        :rtype: dict
        ''' 
        if not self.config_path.exists():
            raise ValueError(f"File does not exists. Check the following path: {self.config_path}")

        try:
            if self.is_encrypted():
                if not self._fernet:
                    raise ValueError("Encryption not initialized. Call initialize_encryption first.")
                
                with open(self.config_path, 'rb') as f:
                    f.readline()
                    data = f.read()
                    if data.endswith(b"\n"):
                        data = data[:-1]
                decrypted_data = self.decrypt_data(data)
                return yaml.safe_load(decrypted_data)
            
            else:
                with open(self.config_path, 'rb') as f:
                    data = f.read()
                return yaml.safe_load(data)
        
        except PermissionError as e:
            raise ValueError(f"Cannot access configuration file: {e}") from e
        

    def _get_editor_command(self) -> str:
        '''
        Try to get editor from environment, fallbacks on nano.

        :return: Editor command name
        :rtype: str
        '''
        if os.name == 'nt':  # Windows, why do I bother??
            editor = os.environ.get('VISUAL')
            if not editor:
                editor = os.environ.get('EDITOR')
            
            if not editor:
                program_files = os.environ.get('ProgramFiles', 'C:\\Program Files')
                vscode_path = os.path.join(program_files, 'Microsoft VS Code', 'Code.exe')
                notepad_plus_path = os.path.join(program_files, 'Notepad++', 'notepad++.exe')
                
                if os.path.exists(vscode_path):
                    editor = vscode_path
                elif os.path.exists(notepad_plus_path):
                    editor = notepad_plus_path
                else:
                    editor = 'notepad.exe'
        
        else:  # Unix-like systems (Linux, macOS)
            editor = os.environ.get('VISUAL')
            if not editor:
                editor = os.environ.get('EDITOR')
            
            if not editor:
                for common_editor in ['nano', 'vim', 'nvim', 'vi', 'emacs']:
                    try:
                        if subprocess.run(['which', common_editor], 
                                    capture_output=True, 
                                    check=False).returncode == 0:
                            editor = common_editor
                            break
                    except Exception:
                        continue
                
                # If no editor found, default to nano
                if not editor:
                    editor = 'nano'
        
        return editor
    


    def edit_config(self):
        '''
        Open the editor with the decrypted file for editing.
        Uses tempfile to store modification before saving it to the configuration YAML file.
        '''
        current_config = self.load_config()
        
        temp_path = self.config_path.with_suffix('.editing.yaml')
        
        try:
            with open(temp_path, 'w') as f:
                yaml.dump(current_config, f, default_flow_style=False) #N.B.: Flow style on false means no inline yaml
            
            os.chmod(temp_path, stat.S_IRUSR | stat.S_IWUSR)
            
            mtime_before = temp_path.stat().st_mtime # Last modifications
            
            editor = self._get_editor_command()
            subprocess.run([editor, str(temp_path)], check=True)
            
            mtime_after = temp_path.stat().st_mtime
            
            if mtime_after > mtime_before:
                with open(temp_path, 'r') as f:
                    try:
                        new_config = yaml.safe_load(f)
                    except yaml.YAMLError as e:
                        raise ValueError(f"Invalid YAML after editing: {e}")
                
                # Save and encrypt the new config
                self.save_config(new_config)
                print("Configuration updated and encrypted.")
            else:
                print("No changes made to configuration.")
                
        finally:
            if temp_path.exists():
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass

    def _add_newlines(self, data: bytes) -> bytes:
        string = data.decode("utf-8")

        # Insert a newline every 80 characters
        new_string = '\n'.join(string[i:i+80] for i in range(0, len(string), 80))
        byte_string = new_string.encode("utf-8")
        
        return byte_string

    def _remove_newlines(self, data: bytes) -> bytes:
        string = data.decode("utf-8")
        # Remove all newline characters
        stripped_string = string.replace('\n', '')

        stripped_byte_string = stripped_string.encode("utf-8")
        
        return stripped_byte_string