#!/usr/bin/env python3


import base64
import os
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import yaml
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class SecureConfig:
    """A class for securely handling configuration files for a specific tool.

    The class manages configuration paths and provides encryption and decryption for sensitive configuration YAMLs.

    Args:
        tool_name (str): The name of the tool.
        config_path (Path, optional): An optional path to the configuration file. If not provided, the default config path will be used.

    """

    def __init__(self, tool_name: str, config_path: Path = None) -> None:
        """Initializes the SecureConfig object with a tool name and configuration path.

        If no configuration path is provided, the default configuration path will be used.

        Args:
            tool_name (str): The name of the tool.
            config_path (Path, optional): An optional path to the configuration file. If not provided, the default config path will be used.

        Returns:
            None

        """
        self.tool_name = tool_name
        self.b_tool_name = tool_name.encode("utf-8")
        self.mngt = b"# MANAGED BY " + self.b_tool_name + b" #\n"
        if config_path is not None:
            self.config_path = (
                config_path if isinstance(config_path, Path) else Path(config_path)
            )
        else:
            self.config_path = self._get_default_config_path()
        self._fernet: Optional[Fernet] = None

    def _get_default_config_path(self) -> Path:
        """Default configuration path.

        Returns:
            Path: Path to the configuration file.

        """
        if os.name == "nt":  # Windows
            base_path = Path(os.environ.get("APPDATA", Path.home()))
            config_dir = base_path / self.tool_name
        elif os.name == "posix":  # Linux/Unix/macOS
            base_path = Path.home()
            if os.path.exists("/Library"):  # macOS
                config_dir = (
                    base_path / "Library" / "Application Support" / self.tool_name
                )
            else:  # Linux/Unix
                config_dir = base_path / ".config" / self.tool_name

        # Create directory with secure permissions
        config_dir.mkdir(parents=True, exist_ok=True)
        if os.name == "posix":
            os.chmod(config_dir, stat.S_IRWXU)
        settings_path_yaml = Path.joinpath(config_dir, "settings.yaml")
        settings_path_yml = Path.joinpath(config_dir, "settings.yml")
        if settings_path_yaml.is_file():
            return settings_path_yaml
        elif settings_path_yml.is_file():
            return settings_path_yml
        raise SystemExit(
            f"settings.yaml does not exists, please check {config_dir}\
                         \nOr make a new one with 'saber -x' and 'saber -e PATH'"
        )

    def get_config_path(self) -> Path:
        """Return stored configuration path.

        Returns:
            Path: Path to the configuration file.

        """
        return self.config_path

    def _derive_key(self, password: str) -> bytes:
        """Derive an encryption key from a password using PBKDF2HMAC with SHA256.

        Uses a static salt value for key derivation.

        Args:
            password (str): The password string to derive the key from.

        Returns:
            bytes: The derived encryption key.

        Note:
            The static salt should be replaced with a properly generated random salt
            to improve security.

        """
        static_salt = b"static_salt_value_777"  # TODO: Use seasoning properly

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(), length=32, salt=static_salt, iterations=100000
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    def _set_secure_permissions(self) -> None:
        """Set secure file permissions on the configuration file.

        On Unix-like systems, sets the file permissions to 600 (user read/write only).
        On Windows systems... well...

        Returns:
            None

        """
        if os.name == "posix":
            os.chmod(self.config_path, stat.S_IRUSR | stat.S_IWUSR)  # 600 permissions

    def encrypt_data(self, data: bytes) -> bytes:
        """Data encryption with Fernet.

        Args:
            data (bytes): Data to encrypt.

        Returns:
            bytes: Encrypted data.

        """
        if not self._fernet:
            raise ValueError(
                "Encryption not initialized. Call initialize_encryption first."
            )
        return self._add_newlines(self._fernet.encrypt(data))

    def decrypt_data(self, encrypted_data: bytes) -> bytes:
        """Data decryption with Fernet.

        Args:
            encrypted_data (bytes): Data to decrypt.

        Returns:
            bytes: Decrypted data.

        """
        if not self._fernet:
            raise ValueError(
                "Encryption not initialized. Call initialize_encryption first."
            )
        return self._fernet.decrypt(self._remove_newlines(encrypted_data))

    def initialize_encryption(self, password: str) -> None:
        """Fernet initialization with derived key.

        Args:
            password (str): String for key derivation.

        Returns:
            None

        """
        key = self._derive_key(password)
        self._fernet = Fernet(key)

    def is_encrypted(self) -> bool:
        """Checks whether the configuration file is encrypted.

        The function check for the presence of a string at the beginning of the file.
        If present the function assumes that the file is encrypted by the same python tool.

        Returns:
            bool: True if the configuration file is encrypted, otherwise False.

        """
        try:
            with open(self.config_path, "rb") as f:
                data = f.readline()

            if data == self.mngt:
                return True
            else:
                return False

        except Exception:
            return False

    def _write_file(self, data: bytes) -> None:
        """Safely write data to the configuration file using atomic operations.

        Uses a temporary file to ensure atomic writes and prevent corruption.
        First attempts to use tempfile.NamedTemporaryFile, falling back to
        a same-directory temporary file if that fails.

        Args:
            data (bytes): The binary data to write to the file.

        Raises:
            OSError: If file operations fail.
            Exception: If any error occurs during file operations.

        """
        # Try using tempfile and replace, can fail in some cases
        try:
            with tempfile.NamedTemporaryFile(mode="wb", delete=False) as tmp_file:
                tmp_file.write(data)
                tmp_file.flush()  # Ensure data is written
                os.fsync(tmp_file.fileno())  # Force write to disk
                tmp_path = Path(tmp_file.name)

            os.chmod(tmp_path, stat.S_IRUSR | stat.S_IWUSR)

            os.replace(
                tmp_path, self.config_path
            )  # Either succed or fails to replace file

        except OSError:
            # Fallback: Use same-directory temporary file
            temp_path = self.config_path.with_suffix(".tmp")
            try:
                # Write encrypted data to temporary file
                with open(temp_path, "wb") as f:
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

    def encrypt_existing_file(self) -> None:
        """Encrypt an existing configuration YAML file.

        Validates YAML format before encryption.

        Returns:
            None

        Raises:
            ValueError: If encryption not initialized or invalid YAML data.
            FileNotFoundError: If configuration file not found.

        """
        if not self._fernet:
            raise ValueError(
                "Encryption not initialized. Call initialize_encryption first."
            )

        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file {self.config_path} not found")

        if not self.is_encrypted():
            # Read and validate the existing YAML file
            with open(self.config_path, "rb") as f:
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

    def decrypt_existing_file(self) -> None:
        """Decrypt an existing configuration YAML file.

        Returns:
            None

        Raises:
            ValueError: If encryption not initialized.
            FileNotFoundError: If configuration file not found.

        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file {self.config_path} not found")

        if self.is_encrypted():
            if not self._fernet:
                raise ValueError(
                    "Encryption not initialized. Call initialize_encryption first."
                )

            with open(self.config_path, "rb") as f:
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

    def _edit_save_config(self, config_data: any) -> None:
        """Save encrypted data to configuration file.

        Args:
            config_data (any): Configuration data.

        Returns:
            None

        Raises:
            ValueError: If encryption not initialized.

        """
        if not self._fernet:
            raise ValueError(
                "Encryption not initialized. Call initialize_encryption first."
            )

        if config_data and not config_data.endswith(b"\n"):
            config_data += b"\n"

        encrypted_data = self.mngt + self.encrypt_data(config_data) + b"\n"

        self._write_file(encrypted_data)

        self._set_secure_permissions()

    def load_config(self) -> dict:
        """Load configuration from YAML file whether is encrypted or not.

        Returns:
            dict: Configuration dictionary.

        Raises:
            ValueError: If file does not exist, encryption not initialized, or cannot access configuration file.

        """
        if not self.config_path.exists():
            raise ValueError(
                f"File does not exists. Check the following path: {self.config_path}"
            )

        try:
            if self.is_encrypted():
                if not self._fernet:
                    raise ValueError(
                        "Encryption not initialized. Call initialize_encryption first."
                    )

                with open(self.config_path, "rb") as f:
                    f.readline()
                    data = f.read()
                    if data.endswith(b"\n"):
                        data = data[:-1]
                decrypted_data = self.decrypt_data(data)
                return yaml.safe_load(decrypted_data)

            else:
                with open(self.config_path, "rb") as f:
                    data = f.read()
                return yaml.safe_load(data)

        except PermissionError as e:
            raise ValueError(f"Cannot access configuration file: {e}") from e

    def _edit_load_config(self) -> any:
        """Load configuration from YAML file whether is encrypted or not as simple text, for editing.

        Returns:
            any: Configuration stream.

        Raises:
            ValueError: If file does not exist, encryption not initialized, or cannot access configuration file.

        """
        if not self.config_path.exists():
            raise ValueError(
                f"File does not exists. Check the following path: {self.config_path}"
            )

        try:
            if self.is_encrypted():
                if not self._fernet:
                    raise ValueError(
                        "Encryption not initialized. Call initialize_encryption first."
                    )

                with open(self.config_path, "rb") as f:
                    f.readline()
                    data = f.read()
                    if data.endswith(b"\n"):
                        data = data[:-1]
                decrypted_data = self.decrypt_data(data)
                return decrypted_data

            else:
                with open(self.config_path, "rb") as f:
                    data = f.read()
                return data

        except PermissionError as e:
            raise ValueError(f"Cannot access configuration file: {e}") from e

    def _get_editor_command(self) -> str:
        """Try to get editor from environment, fallbacks on nano.

        Returns:
            str: Editor command name.

        """
        if os.name == "nt":  # Windows, why do I bother??
            editor = os.environ.get("VISUAL")
            if not editor:
                editor = os.environ.get("EDITOR")

            if not editor:
                program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
                vscode_path = os.path.join(
                    program_files, "Microsoft VS Code", "Code.exe"
                )
                notepad_plus_path = os.path.join(
                    program_files, "Notepad++", "notepad++.exe"
                )

                if os.path.exists(vscode_path):
                    editor = vscode_path
                elif os.path.exists(notepad_plus_path):
                    editor = notepad_plus_path
                else:
                    editor = "notepad.exe"

        else:  # Unix-like systems (Linux, macOS)
            editor = os.environ.get("VISUAL")
            if not editor:
                editor = os.environ.get("EDITOR")

            if not editor:
                for common_editor in ["nano", "vim", "nvim", "vi", "emacs"]:
                    try:
                        if (
                            subprocess.run(
                                ["which", common_editor],
                                capture_output=True,
                                check=False,
                            ).returncode
                            == 0
                        ):
                            editor = common_editor
                            break
                    except Exception:
                        continue

                # If no editor found, default to nano
                if not editor:
                    editor = "nano"

        return editor

    def edit_config(self) -> None:
        """Open the editor with the decrypted file for editing.

        Uses tempfile to store modification before saving it to the configuration YAML file.

        Raises:
            ValueError: If invalid YAML after editing.

        """
        current_config = self._edit_load_config()

        temp_path = self.config_path.with_suffix(".editing.yaml")

        try:
            with open(temp_path, "wb") as f:
                f.write(current_config)

            os.chmod(temp_path, stat.S_IRUSR | stat.S_IWUSR)

            mtime_before = temp_path.stat().st_mtime  # Last modifications

            editor = self._get_editor_command()
            subprocess.run([editor, str(temp_path)], check=True)

            mtime_after = temp_path.stat().st_mtime

            if mtime_after > mtime_before:
                with open(temp_path, "rb") as f:
                    new_config = f.read()
                try:
                    yaml.safe_load(new_config)
                except yaml.YAMLError as e:
                    raise ValueError(f"Invalid YAML after editing: {e}")

                # Save and encrypt the new config
                self._edit_save_config(new_config)
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
        """Format encrypted data by adding newlines for better readability.

        Splits the encrypted data into lines of 80 characters each to make
        the encrypted file more pleasing when viewed in a text editor.

        Args:
            data: The encrypted binary data to format

        Returns:
            bytes: The formatted data with newlines inserted every 80 characters

        """
        string = data.decode("utf-8")

        # Insert a newline every 80 characters
        new_string = "\n".join(string[i : i + 80] for i in range(0, len(string), 80))
        byte_string = new_string.encode("utf-8")

        return byte_string

    def _remove_newlines(self, data: bytes) -> bytes:
        """Remove formatting newlines from encrypted data before decryption.

        Reverses the effect of _add_newlines() by removing all newline characters
        before attempting to decrypt the data.

        Args:
            data: The formatted encrypted data with newlines

        Returns:
            bytes: The original encrypted data without newlines

        """
        string = data.decode("utf-8")
        # Remove all newline characters
        stripped_string = string.replace("\n", "")

        stripped_byte_string = stripped_string.encode("utf-8")

        return stripped_byte_string
