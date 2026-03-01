import logging
import sys

from colorama import Fore

from GramAddict.core.device_facade import Timeout
from GramAddict.core.resources import ResourceID, ClassName
from GramAddict.core.views import (
    HashTagView,
    PlacesView,
    PostsGridView,
    ProfileView,
    TabBarView,
)

logger = logging.getLogger(__name__)


def check_if_english(device):
    """check if app is in English"""
    logger.debug("Checking if app is in English..")
    # If user specified app language in config, honor it and skip strict English check
    try:
        from GramAddict.core.utils import configs

        app_lang = getattr(configs.args, "app_language", None)
    except Exception:
        app_lang = None
    if app_lang:
        logger.info(f"App language forced by config: {app_lang}. Skipping English check.")
        return ProfileView(device, is_own_profile=True)
    # Fast-path: try to read familiar header labels directly (very quick)
    try:
        # First, try container content-descs which are often present and very fast
        try:
            post_ctn = device.find(resourceId=ResourceID.PROFILE_HEADER_POST_COUNT_FRONT_FAMILIAR)
            foll_ctn = device.find(resourceId=ResourceID.PROFILE_HEADER_FOLLOWERS_STACKED_FAMILIAR)
            follow_ctn = device.find(resourceId=ResourceID.PROFILE_HEADER_FOLLOWING_STACKED_FAMILIAR)
            if post_ctn.exists(Timeout.TINY):
                desc = post_ctn.get_desc() or ""
                if "post" in desc.casefold():
                    # quick acceptance if container descriptions include labels
                    logger.debug("Instagram in English (fast-path via content-desc).")
                    return ProfileView(device, is_own_profile=True)
            if foll_ctn.exists(Timeout.TINY) and follow_ctn.exists(Timeout.TINY):
                d1 = foll_ctn.get_desc() or ""
                d2 = follow_ctn.get_desc() or ""
                if "follower" in d1.casefold() and "follow" in d2.casefold():
                    logger.debug("Instagram in English (fast-path via content-desc stacked).")
                    return ProfileView(device, is_own_profile=True)
        except Exception:
            # continue to label-based checks
            pass
        post_label = device.find(
            resourceId=ResourceID.PROFILE_HEADER_FAMILIAR_POST_COUNT_LABEL,
            className=ClassName.TEXT_VIEW,
        )
        followers_label = device.find(
            resourceId=ResourceID.PROFILE_HEADER_FAMILIAR_FOLLOWERS_LABEL,
            className=ClassName.TEXT_VIEW,
        )
        following_label = device.find(
            resourceId=ResourceID.PROFILE_HEADER_FAMILIAR_FOLLOWING_LABEL,
            className=ClassName.TEXT_VIEW,
        )
        if (
            post_label.exists(Timeout.TINY)
            and followers_label.exists(Timeout.TINY)
            and following_label.exists(Timeout.TINY)
        ):
            p = (post_label.get_text(error=False) or "").casefold()
            f = (followers_label.get_text(error=False) or "").casefold()
            g = (following_label.get_text(error=False) or "").casefold()
            if p == "posts" and f == "followers" and g == "following":
                logger.debug("Instagram in English (fast-path).")
                return ProfileView(device, is_own_profile=True)
    except Exception:
        # fallback to full extraction
        pass

    post, follower, following = ProfileView(device)._getSomeText()
    if None in {post, follower, following}:
        logger.warning(
            "Failed to check your Instagram language. Be sure to set it to English or the bot won't work!"
        )
    elif post == "posts" and follower == "followers" and following == "following":
        logger.debug("Instagram in English.")
    else:
        logger.error("Please change the language manually to English!")
        sys.exit(1)
    return ProfileView(device, is_own_profile=True)


def nav_to_blogger(device, username, current_job):
    """navigate to blogger (followers list or posts)"""
    _to_followers = bool(current_job.endswith("followers"))
    _to_following = bool(current_job.endswith("following"))
    if username is None:
        profile_view = TabBarView(device).navigateToProfile()
        if _to_followers:
            logger.info("Open your followers.")
            profile_view.navigateToFollowers()
        elif _to_following:
            logger.info("Open your following.")
            profile_view.navigateToFollowing()
    else:
        search_view = TabBarView(device).navigateToSearch()
        if not search_view.navigate_to_target(username, current_job):
            return False

        profile_view = ProfileView(device, is_own_profile=False)
        if _to_followers:
            logger.info(f"Open @{username} followers.")
            profile_view.navigateToFollowers()
        elif _to_following:
            logger.info(f"Open @{username} following.")
            profile_view.navigateToFollowing()

    return True


def nav_to_hashtag_or_place(device, target, current_job):
    """navigate to hashtag/place/feed list"""
    search_view = TabBarView(device).navigateToSearch()
    if not search_view.navigate_to_target(target, current_job):
        return False
    
    TargetView = HashTagView if current_job.startswith("hashtag") else PlacesView

    # if current_job.endswith("recent"):
    #     logger.info("Switching to Recent tab.")
    #     recent_tab = TargetView(device)._getRecentTab()

    #     # Save a quick debug dump (hierarchy + screenshot) after search to help locate posts
    # try:
    #     low_level_device = getattr(device, "deviceV2", device)
    #     debug_logger.save_dump(low_level_device, reason=f"search_{target}", extra={"job": current_job})
    # except Exception:
    #     # Don't block navigation on debug failure
    #     logger.debug("Failed to save debug dump after search.", exc_info=True)

    #     if recent_tab.exists(Timeout.MEDIUM):
    #         recent_tab.click()
    #     else:
    #         return False

    #     if UniversalActions(device)._check_if_no_posts():
    #         UniversalActions(device)._reload_page()
    #         if UniversalActions(device)._check_if_no_posts():
    #             return False

    result_view = TargetView(device)._getRecyclerView()
    FistImageInView = TargetView(device)._getFistImageView(result_view)
    if FistImageInView.exists():
        logger.info(f"Opening the first result for {target}.")
        FistImageInView.click()
        return True
    else:
        logger.info(
            f"There is any result for {target} (not exists or doesn't load). Skip."
        )
        return False


def nav_to_post_likers(device, username, my_username):
    """navigate to blogger post likers"""
    if username == my_username:
        TabBarView(device).navigateToProfile()
    else:
        search_view = TabBarView(device).navigateToSearch()
        if not search_view.navigate_to_target(username, "account"):
            return False
    profile_view = ProfileView(device)
    is_private = profile_view.isPrivateAccount()
    posts_count = profile_view.getPostsCount()
    is_empty = posts_count == 0
    if is_private or is_empty:
        private_empty = "Private" if is_private else "Empty"
        logger.info(f"{private_empty} account.", extra={"color": f"{Fore.GREEN}"})
        return False
    logger.info(f"Opening the first post of {username}.")
    ProfileView(device).swipe_to_fit_posts()
    PostsGridView(device).navigateToPost(0, 0)
    return True


def nav_to_feed(device):
    TabBarView(device).navigateToHome()
