__all__ = []
try:
    from .utils import download_arxiv_pdf, download_semantic_scholar_pdf, download_google_scholar_paper, download_papers_using_pypaperbot  # noqa
    from .academia_downloader import download_academia_pdf  # noqa
    from .oa_downloader import download_oa_papers  # noqa
    __all__.append('download_arxiv_pdf')
    __all__.append('download_semantic_scholar_pdf')
    __all__.append('download_google_scholar_paper')
    __all__.append('download_academia_pdf')
    __all__.append('download_oa_papers')
    __all__.append('download_papers_using_pypaperbot')
except ImportError as e:
    print(e)