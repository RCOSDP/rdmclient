**GakuNin RDMを操作する​コマンドラインツール​**

**要旨：**
コマンドラインツールのPythonコードをGitHubに於いて公開中。GakuNin RDMユーザアカウントでCLIからファイル・フォルダのリスト・アップロード・ダウンロード操作が可能。

https://github.com/RCOSDP/rdmclient​


**利用方法：**
ユーザ情報設定画面で生成される「パーソナルアクセストークン」と、GakuNin RDMプロジェクトの「GUID」を利用​「パーソナルアクセストークン」はパスワード等と同様、セキュアな管理が必須​


**rdmclientのインストール方法**

1.) GitHubのリポジトリ rdmclientのmasterブランチをgit clone​

    https://github.com/RCOSDP/rdmclient​

2.) Pythonの仮想実行環境 pyenv をインストールして、activateする。​

    % pyenv virtualenv <Pythonバージョン> <Python仮想環境名>​
    
    % pyenv activate <Pyton仮想環境名>​

3.) rdmclient ファイルのディレクト中で必要なPythonパッケージをpipでインストール。​

    % pip install -r requirements.txt​

（仮想環境でなくオプションで--break-system-packagesを使う方法もある。）​

4.) rdmclient ファイルのディレクト中でpipを使ってインストール​

    % cd ./rdmclient​
    
    % pip install . ​

（仮想環境でなくオプションで--break-system-packagesを使う方法もある。）​

5.) インストールの確認​

    % osf -v ​
    
    osf 0.0.4​

6.) GRDMのユーザせて値画面でパーソナルアクセストークンを払い出して、環境変数OSF_TOKENへ設定。​

    % export OSF_TOKEN=<GRDMパーソナルアクセストークン>​

7.) 【実行例】lsコマンドを実行。​

    % osf --base-url https://api.rdm.nii.ac.jp/v2/ -p <プロジェクト名>  ls​
＊% osf init はGakuNin RDMでは使用しない。​


**実行例：rdmclientの基本コマンド**

1.) rdmclientのコマンドのヘルフを表示​

    % osf help​

2.) GRDMのプロジェクト中のファイル一覧を取得​

    % osf --base-url https://api.rdm.nii.ac.jp/v2/ -p <プロジェクト名>  ls (または) osf list​

3.) GRDMのプロジェクトへファイルをアップロード​

    % osf --base-url https://api.rdm.nii.ac.jp/v2/ -p <プロジェクト名> upload <ローカルの転送元のファイル名> <GRDM上の保存先パス> ​

＊-r を指定することで、カレントディレクトリ中のファイルの再帰的なアップロードが可能です。​

4.) GRDMのプロジェクトへディレクトリを作成​

    % osf --base-url https://api.rdm.nii.ac.jp/v2/ -p <プロジェクト名> mkdir <作成するディレクトリのパス/ディレクトリ名>（または）makefolder​


5.) GRDM上のプロジェクト中のファイルの取得​

    % osf --base-url https://api.rdm.nii.ac.jp/v2/ -p <プロジェクト名> fetch <GRDM上のファイルのパス/ファイル名> <ローカルの保存先>​


6.) GRDM上のプロジェクト中の全ファイルの取得​

    % osf --base-url https://api.rdm.nii.ac.jp/v2/ -p <プロジェクト名> clone <ローカルの保存先のパス/ディレクトリ>​

7.) GRDM上のプロジェクト中のファイルの移動​

    % osf --base-url https://api.rdm.nii.ac.jp/v2/ -p <プロジェクト名> mv  <GRDM上の移動元ファイルのパス/ファイル名>   <GRDM上の移動先のファイルのパス>（または）move​

8.) GRDM上のプロジェクト中のファイルの削除​

    % osf --base-url https://api.rdm.nii.ac.jp/v2/ -p <プロジェクト名> rm <GRDM上のファイルのパス/ファイル名>（または）remove​


