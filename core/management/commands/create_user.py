"""Create an admin, trainer, or trainee CustomUser account from the command line."""
from getpass import getpass

from django.core.management.base import BaseCommand, CommandError, CommandParser

from core.models import CustomUser


class Command(BaseCommand):
    help = (
        "Create a CustomUser account of a given role (admin, trainer, or trainee). "
        "Intended as the bootstrap path for the first admin account and for seeding "
        "a fresh deployment before any trainer exists to use the in-app forms."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--role",
            required=True,
            choices=["admin", "trainer", "trainee"],
            help="Account kind to create.",
        )
        parser.add_argument("--username", required=True, help="Login username.")
        parser.add_argument("--email", default="", help="Email address (optional).")
        parser.add_argument(
            "--password",
            default=None,
            help=(
                "Password. If omitted, you will be prompted twice with hidden input. "
                "Passing it here is supported for scripted seeding but is less safe "
                "(it can land in shell history)."
            ),
        )
        parser.add_argument(
            "--head-trainer",
            default=None,
            help="Username of the trainer to assign as head_trainer (only used with --role trainee).",
        )

    def handle(self, *args: object, **options: object) -> None:
        role: str = options["role"]
        username: str = options["username"]
        email: str = options["email"]
        password: str | None = options["password"]
        head_trainer_username: str | None = options["head_trainer"]

        if CustomUser.objects.filter(username=username).exists():
            raise CommandError(f"A user named '{username}' already exists.")

        head_trainer: CustomUser | None = None
        if head_trainer_username:
            if role != "trainee":
                self.stderr.write(
                    self.style.WARNING(
                        "--head-trainer is only used with --role trainee; ignoring it."
                    )
                )
            else:
                try:
                    head_trainer = CustomUser.objects.get(username=head_trainer_username)
                except CustomUser.DoesNotExist:
                    raise CommandError(
                        f"No user named '{head_trainer_username}' exists."
                    )
                if head_trainer.role != "trainer":
                    raise CommandError(
                        f"'{head_trainer_username}' is not a trainer (role="
                        f"'{head_trainer.role}')."
                    )

        if password is None:
            password = self._prompt_for_password()

        if role == "admin":
            user = CustomUser.objects.create_superuser(
                username=username, email=email, password=password
            )
        else:
            user = CustomUser.objects.create_user(
                username=username, email=email, password=password
            )
            user.role = role
            if head_trainer is not None:
                user.head_trainer = head_trainer
            user.save()

        self.stdout.write(
            self.style.SUCCESS(f"Created {role} '{user.username}' (id={user.pk}).")
        )

    def _prompt_for_password(self) -> str:
        while True:
            password = getpass("Password: ")
            confirm = getpass("Password (again): ")
            if password != confirm:
                self.stderr.write(self.style.ERROR("Passwords did not match. Try again."))
                continue
            if not password:
                self.stderr.write(self.style.ERROR("Password cannot be empty. Try again."))
                continue
            return password
