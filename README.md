# PonteGlam

Brief project description.

<br>

## Requirements

- Python >= 3.11.2
- PostgreSQL >= 16.1

<br>

## Installation

1. Clone the repository:

    ```bash
    git clone git@github.com:blackfenixsoft/PonteGlamBackend.git
    ```

2. Create a virtual environment (optional but recommended):

    ```bash
    python -m venv env
    ```

3. Activate the virtual environment:

    - Windows:

        ```bash
        .\env\Scripts\activate
        ```

    - macOS/Linux:

        ```bash
        source env/bin/activate
        ```

4. Navigate to the project directory:

    ```bash
    cd PonteGlamBackend
    ```

5. Install the dependencies:

    ```bash
    pip install update pip
    pip install -r requirements.txt
    ```

6. Generate and apply migrations
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

7. Run the project:
    ```bash
    python manage.py runserver
    ```

### If it becomes necessary to update the database

1. Delete the current database and recreate it
    ```bash
    sudo su postgres
    psql
    DROP DATABASE dbpg;
    CREATE DATABASE dbpg;
    ```

2. Delete the migration files
    ```bash
    find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
    find . -path "*/migrations/*.pyc" -delete
    ```

3. Generate and apply migrations
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

4. Update the database
    ```bash
    Insertar aqui el comando ...
    ```

<br>

## Configuration

### Setting up Pre-commit (Optional)

1. **Install pre-commit**:

   When installing the requirements.txt, the pre-commit library is already installed. To install and configure the hook, you must run the following command:

   ```bash
   pre-commit install
   ```

2. **Auto-update pre-commit hooks:**:

    To ensure that your pre-commit hooks stay up-to-date, you can enable auto-update by running the following command:

    ```bash
   pre-commit autoupdate
   ```

3. **Running pre-commit:**:

    Now that the pre-commit hooks are installed and configured, they will run automatically in your local repository when committing. <br>
    To do so, first add your changes using the command: ` git add . ` <br>
    Then commit using: ` git commit `. <br>
    You will see the hooks being executed during the commit process.

### Why Use Pre-commit?

Pre-commit is a powerful tool that helps maintain code quality and consistency in your projects. By automatically running checks and tasks before each commit, pre-commit ensures that your code meets certain standards and guidelines. Some of the advantages of using pre-commit include:

- **Consistency**: Enforces consistent coding styles and formatting across your codebase.
- **Error Prevention**: Helps catch common errors and issues early in the development process, reducing the likelihood of introducing bugs.
- **Automated Workflow**: Streamlines your development workflow by automating repetitive tasks such as linting, formatting, and code analysis.
- **Improved Collaboration**: Facilitates collaboration among team members by providing a standardized set of checks and practices.
- **Time Savings**: Saves time by identifying and fixing issues before they become larger problems.

In summary, pre-commit is an essential tool for any development team looking to improve code quality, reduce errors, and streamline their development process.

<br>

## Usage

Explain how to use the project, for example, how to run the server, how to access the application, etc.

<br>

## Contribution and Branching Strategy

To contribute to the project, follow these steps:

1. Clone the repository and navigate to the project directory.

2. Create a new branch for your feature/bugfix with the following format: `R-<requirement_number>`.

3. Make your changes, ensure the tests pass, and commit your changes with the specified structure.

4. Push the branch and submit a pull request for your changes to be reviewed.

### Branching Strategy

In this project, we follow a specific branching strategy:

- `main`: Production branch.
- `release`: Integration branch, one step before production.
- `test`: Branch for conducting various functional tests on the adjustments made.
- `R-<requirement_number>`: Branch for specific requirements, whether it's a fix, an enhancement, or a new feature.

When a developer wants to make changes or add a feature, they should request a requirement number and create a branch from `main` with the name `R-<requirement_number>`.

### Example Commit Structure:

Suppose you are working on requirement number 123 and fixing a bug related to user authentication. Your commit structure would be:

```bash
git commit -m "[R-123] : Fix - Fix user authentication bug"
```

<br>

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).
